# Multi-Agent Systems

When multiple agents work together, coordination becomes essential. This guide covers communication, role assignment, and collaborative strategies.

## Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT SYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐                │
│   │ Agent A │    │ Agent B │    │ Agent C │                │
│   │ (Scout) │    │ (Gather)│    │ (Build) │                │
│   └────┬────┘    └────┬────┘    └────┬────┘                │
│        │              │              │                       │
│        └──────────────┼──────────────┘                       │
│                       │                                      │
│              ┌────────┴────────┐                            │
│              │ Shared Blackboard│                            │
│              │  - Known locations│                           │
│              │  - Resource claims │                          │
│              │  - Task status     │                          │
│              └─────────────────┘                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## The Blackboard Pattern

A shared space where agents post and read information:

```python
from dataclasses import dataclass, field
from typing import Any
from threading import Lock
from collections import defaultdict


@dataclass
class BlackboardEntry:
    """An entry on the blackboard."""
    key: str
    value: Any
    posted_by: str
    tick: int
    expires_at: int | None = None  # None = never expires


class Blackboard:
    """Shared communication space for multiple agents."""

    def __init__(self):
        self._entries: dict[str, BlackboardEntry] = {}
        self._subscriptions: dict[str, list[str]] = defaultdict(list)  # topic -> [agent_ids]
        self._lock = Lock()

    def post(self, key: str, value: Any, agent_id: str, tick: int,
             ttl: int | None = None) -> None:
        """Post an entry to the blackboard."""
        with self._lock:
            expires = tick + ttl if ttl else None
            self._entries[key] = BlackboardEntry(
                key=key,
                value=value,
                posted_by=agent_id,
                tick=tick,
                expires_at=expires
            )

    def read(self, key: str, current_tick: int) -> Any | None:
        """Read an entry from the blackboard."""
        with self._lock:
            entry = self._entries.get(key)
            if entry:
                if entry.expires_at and current_tick > entry.expires_at:
                    del self._entries[key]
                    return None
                return entry.value
            return None

    def read_all(self, prefix: str, current_tick: int) -> dict[str, Any]:
        """Read all entries matching a prefix."""
        with self._lock:
            result = {}
            expired = []
            for key, entry in self._entries.items():
                if key.startswith(prefix):
                    if entry.expires_at and current_tick > entry.expires_at:
                        expired.append(key)
                    else:
                        result[key] = entry.value
            for key in expired:
                del self._entries[key]
            return result

    def claim_resource(self, resource_id: str, agent_id: str, tick: int) -> bool:
        """Try to claim exclusive access to a resource."""
        key = f"claim:{resource_id}"
        with self._lock:
            existing = self._entries.get(key)
            if existing and existing.value != agent_id:
                # Already claimed by someone else
                return False
            self._entries[key] = BlackboardEntry(
                key=key,
                value=agent_id,
                posted_by=agent_id,
                tick=tick,
                expires_at=tick + 10  # Claim expires after 10 ticks
            )
            return True

    def release_claim(self, resource_id: str, agent_id: str) -> None:
        """Release a resource claim."""
        key = f"claim:{resource_id}"
        with self._lock:
            entry = self._entries.get(key)
            if entry and entry.value == agent_id:
                del self._entries[key]


# Global blackboard instance
_blackboard = Blackboard()


def get_blackboard() -> Blackboard:
    """Get the global blackboard instance."""
    return _blackboard
```

## Role-Based Agents

Define specialized roles for agents:

```python
from enum import Enum
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema


class AgentRole(Enum):
    SCOUT = "scout"       # Explores and reports
    GATHERER = "gatherer" # Collects resources
    BUILDER = "builder"   # Crafts items
    GUARD = "guard"       # Watches for hazards


class RoleBasedAgent(AgentBehavior):
    """Agent that behaves according to its assigned role."""

    def __init__(self, agent_id: str, role: AgentRole):
        self.agent_id = agent_id
        self.role = role
        self.blackboard = get_blackboard()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Post current status
        self._post_status(observation)

        # Role-specific behavior
        if self.role == AgentRole.SCOUT:
            return self._scout_behavior(observation, tools)
        elif self.role == AgentRole.GATHERER:
            return self._gatherer_behavior(observation, tools)
        elif self.role == AgentRole.BUILDER:
            return self._builder_behavior(observation, tools)
        elif self.role == AgentRole.GUARD:
            return self._guard_behavior(observation, tools)

        return AgentDecision.idle()

    def _post_status(self, obs: Observation) -> None:
        """Post current status to blackboard."""
        self.blackboard.post(
            key=f"agent:{self.agent_id}:status",
            value={
                "position": obs.position,
                "health": obs.health,
                "role": self.role.value,
                "inventory_count": len(obs.inventory)
            },
            agent_id=self.agent_id,
            tick=obs.tick,
            ttl=5
        )

    def _scout_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Scout role: explore and report findings."""
        # Report any resources found
        for resource in obs.nearby_resources:
            self.blackboard.post(
                key=f"resource:{resource.name}",
                value={
                    "position": resource.position,
                    "type": resource.type,
                    "reported_by": self.agent_id
                },
                agent_id=self.agent_id,
                tick=obs.tick,
                ttl=50
            )

        # Report hazards
        for hazard in obs.nearby_hazards:
            self.blackboard.post(
                key=f"hazard:{hazard.name}",
                value={
                    "position": hazard.position,
                    "damage": hazard.damage
                },
                agent_id=self.agent_id,
                tick=obs.tick,
                ttl=100  # Hazards don't move, longer TTL
            )

        # Explore unexplored areas
        return self._explore(obs)

    def _gatherer_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Gatherer role: collect resources."""
        # Check blackboard for reported resources
        known_resources = self.blackboard.read_all("resource:", obs.tick)

        # Find unclaimed resource
        for key, data in known_resources.items():
            resource_id = key.replace("resource:", "")
            if self.blackboard.claim_resource(resource_id, self.agent_id, obs.tick):
                # Successfully claimed - go collect
                return AgentDecision(
                    tool="move_to",
                    params={"target_position": list(data["position"])},
                    reasoning=f"Going to collect {resource_id}"
                )

        # No resources to claim - help scout
        return self._explore(obs)

    def _builder_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Builder role: craft items."""
        # Check if we have materials for any recipe
        if "craft" in [t.name for t in tools]:
            # Try to craft something
            return AgentDecision(
                tool="craft",
                params={"recipe": "planks"},
                reasoning="Crafting with available materials"
            )

        # Wait for materials
        return AgentDecision.idle(reasoning="Waiting for materials")

    def _guard_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Guard role: warn about dangers."""
        # Check for nearby hazards and warn team
        for hazard in obs.nearby_hazards:
            if hazard.distance < 5.0:
                self.blackboard.post(
                    key=f"warning:{hazard.name}",
                    value={
                        "type": "danger",
                        "position": hazard.position,
                        "radius": 5.0
                    },
                    agent_id=self.agent_id,
                    tick=obs.tick,
                    ttl=20
                )

        # Patrol between agents
        return self._patrol(obs)

    def _explore(self, obs: Observation) -> AgentDecision:
        """Generic exploration behavior."""
        import random
        import math
        angle = random.uniform(0, 2 * math.pi)
        target = [
            obs.position[0] + 10 * math.cos(angle),
            obs.position[1],
            obs.position[2] + 10 * math.sin(angle)
        ]
        return AgentDecision(
            tool="move_to",
            params={"target_position": target},
            reasoning="Exploring"
        )

    def _patrol(self, obs: Observation) -> AgentDecision:
        """Patrol behavior for guards."""
        # Get other agent positions
        agents = self.blackboard.read_all("agent:", obs.tick)
        positions = [data["position"] for key, data in agents.items()
                    if key != f"agent:{self.agent_id}:status"]

        if positions:
            # Move toward center of team
            center = [
                sum(p[0] for p in positions) / len(positions),
                0,
                sum(p[2] for p in positions) / len(positions)
            ]
            return AgentDecision(
                tool="move_to",
                params={"target_position": center},
                reasoning="Patrolling near team"
            )

        return AgentDecision.idle()
```

## Task Allocation

Dynamically assign tasks to agents:

```python
from dataclasses import dataclass
from typing import Callable


@dataclass
class Task:
    """A task that can be assigned to an agent."""
    id: str
    description: str
    priority: int  # Higher = more important
    required_role: AgentRole | None = None
    assigned_to: str | None = None
    status: str = "pending"  # pending, assigned, in_progress, completed, failed
    location: tuple | None = None


class TaskAllocator:
    """Allocates tasks to agents based on capability and proximity."""

    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.tasks: dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        """Add a task to the pool."""
        self.tasks[task.id] = task
        self.blackboard.post(
            key=f"task:{task.id}",
            value={
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "location": task.location
            },
            agent_id="system",
            tick=0
        )

    def get_task_for_agent(self, agent_id: str, role: AgentRole,
                          position: tuple, tick: int) -> Task | None:
        """Get the best available task for an agent."""
        available = [
            t for t in self.tasks.values()
            if t.status == "pending"
            and (t.required_role is None or t.required_role == role)
        ]

        if not available:
            return None

        # Score tasks by priority and distance
        def score(task: Task) -> float:
            priority_score = task.priority * 10
            if task.location:
                distance = sum((a - b) ** 2 for a, b in zip(position, task.location)) ** 0.5
                distance_penalty = distance * 0.5
            else:
                distance_penalty = 0
            return priority_score - distance_penalty

        best = max(available, key=score)

        # Assign task
        best.assigned_to = agent_id
        best.status = "assigned"
        self.blackboard.post(
            key=f"task:{best.id}",
            value={
                "description": best.description,
                "status": best.status,
                "assigned_to": agent_id
            },
            agent_id="system",
            tick=tick
        )

        return best

    def complete_task(self, task_id: str, tick: int) -> None:
        """Mark a task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id].status = "completed"
            self.blackboard.post(
                key=f"task:{task_id}",
                value={"status": "completed"},
                agent_id="system",
                tick=tick
            )
```

## Coordination Strategies

### Leader-Follower

One agent leads, others follow:

```python
class LeaderFollowerTeam:
    """Team where one agent is the leader."""

    def __init__(self, leader_id: str, follower_ids: list[str]):
        self.leader_id = leader_id
        self.follower_ids = follower_ids
        self.blackboard = get_blackboard()

    def leader_decide(self, obs: Observation) -> AgentDecision:
        """Leader makes decisions and posts orders."""
        # Decide on team action
        if obs.nearby_resources:
            target = obs.nearby_resources[0]
            # Post order for followers
            self.blackboard.post(
                key="team:order",
                value={
                    "action": "gather",
                    "target": target.position,
                    "formation": "spread"
                },
                agent_id=self.leader_id,
                tick=obs.tick,
                ttl=10
            )
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning="Leading team to resource"
            )

        return self._explore(obs)

    def follower_decide(self, obs: Observation, agent_id: str) -> AgentDecision:
        """Follower reads orders and follows."""
        order = self.blackboard.read("team:order", obs.tick)

        if order:
            target = order["target"]
            # Offset position based on formation
            index = self.follower_ids.index(agent_id)
            offset = [(index - 1) * 3, 0, (index - 1) * 3]
            adjusted = [t + o for t, o in zip(target, offset)]

            return AgentDecision(
                tool="move_to",
                params={"target_position": adjusted},
                reasoning=f"Following leader order: {order['action']}"
            )

        # No orders - stay near leader
        leader_status = self.blackboard.read(f"agent:{self.leader_id}:status", obs.tick)
        if leader_status:
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(leader_status["position"])},
                reasoning="Following leader"
            )

        return AgentDecision.idle()
```

### Consensus-Based

Agents vote on decisions:

```python
class ConsensusTeam:
    """Team that makes decisions by consensus."""

    def __init__(self, agent_ids: list[str]):
        self.agent_ids = agent_ids
        self.blackboard = get_blackboard()

    def propose(self, agent_id: str, proposal: dict, tick: int) -> None:
        """Agent proposes an action."""
        self.blackboard.post(
            key=f"proposal:{agent_id}",
            value=proposal,
            agent_id=agent_id,
            tick=tick,
            ttl=5
        )

    def vote(self, agent_id: str, for_proposal: str, tick: int) -> None:
        """Agent votes for a proposal."""
        self.blackboard.post(
            key=f"vote:{agent_id}",
            value=for_proposal,
            agent_id=agent_id,
            tick=tick,
            ttl=5
        )

    def get_consensus(self, tick: int) -> dict | None:
        """Get the proposal with most votes."""
        votes = self.blackboard.read_all("vote:", tick)
        if not votes:
            return None

        # Count votes per proposal
        vote_counts = defaultdict(int)
        for vote in votes.values():
            vote_counts[vote] += 1

        # Need majority
        required = len(self.agent_ids) // 2 + 1
        for proposal_id, count in vote_counts.items():
            if count >= required:
                return self.blackboard.read(f"proposal:{proposal_id}", tick)

        return None
```

## Communication Protocols

### Broadcast Messages

```python
def broadcast(self, message_type: str, content: dict, tick: int) -> None:
    """Broadcast a message to all agents."""
    self.blackboard.post(
        key=f"broadcast:{tick}:{self.agent_id}",
        value={
            "type": message_type,
            "content": content,
            "sender": self.agent_id
        },
        agent_id=self.agent_id,
        tick=tick,
        ttl=10
    )

def receive_broadcasts(self, tick: int) -> list[dict]:
    """Receive all broadcast messages."""
    broadcasts = self.blackboard.read_all("broadcast:", tick)
    return [v for v in broadcasts.values() if v["sender"] != self.agent_id]
```

### Direct Messages

```python
def send_message(self, to_agent: str, content: dict, tick: int) -> None:
    """Send a direct message to another agent."""
    self.blackboard.post(
        key=f"message:{to_agent}:{tick}:{self.agent_id}",
        value={
            "content": content,
            "sender": self.agent_id
        },
        agent_id=self.agent_id,
        tick=tick,
        ttl=10
    )

def receive_messages(self, tick: int) -> list[dict]:
    """Receive messages addressed to this agent."""
    messages = self.blackboard.read_all(f"message:{self.agent_id}:", tick)
    return list(messages.values())
```

## Next Steps

- [Team Challenge](06_team_challenge.md) - Apply multi-agent concepts
