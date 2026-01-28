"""
Test RAGMemory with simulated LLM agent decision-making.

This demonstrates a complete agent loop:
1. Receive observation from environment
2. Query memory for relevant past experiences
3. Build context with memories
4. Make decision (simulated LLM)
5. Store new observation
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("RAG Memory + LLM Agent Simulation")
print("=" * 70)

try:
    from agent_runtime.memory import RAGMemory
    from agent_runtime.schemas import Observation, ResourceInfo, HazardInfo, ItemInfo

    # Mock LLM backend for demonstration
    class MockLLMBackend:
        """Simulates an LLM that uses memory to make decisions."""

        def generate(self, prompt: str) -> str:
            """Simulate LLM response based on context."""
            # In real usage, this would call actual LLM
            if "berries" in prompt.lower() and "food" in prompt.lower():
                return "Based on past experience at position (10.0, 0.0, 5.0), I should search the forest area for berries. I successfully collected 5 berries there before."
            elif "hazard" in prompt.lower() or "fire" in prompt.lower():
                return "Warning: Previous memory shows approaching fire at (22.0, 0.0, 10.0) caused 30 damage. I should maintain distance >3.0 from fire hazards."
            elif "water" in prompt.lower():
                return "Memory indicates water source found near rocks at position (5.0, 0.0, 15.0). Stone was also available nearby."
            else:
                return "Exploring area to gather more information for memory."

    class RAGAgent:
        """An agent that uses RAG memory to inform decisions."""

        def __init__(self, agent_id: str, backend: MockLLMBackend):
            self.agent_id = agent_id
            self.backend = backend
            self.memory = RAGMemory(
                embedding_model="all-MiniLM-L6-v2",
                index_type="FlatIP",
                similarity_threshold=0.2,  # Lower threshold for demo
                default_k=3,
            )
            print(f"[OK] Initialized RAGAgent '{agent_id}'")

        def decide(self, observation: Observation, goal: str) -> str:
            """Make a decision based on current observation and memory."""

            # Store current observation
            self.memory.store(observation)
            print(f"\n[STORE] Tick {observation.tick} - Position {observation.position}")
            print(f"        Health: {observation.health}, Energy: {observation.energy}")

            # Query memory for relevant past experiences
            print(f"\n[QUERY] Goal: '{goal}'")
            relevant_memories = self.memory.retrieve(query=goal, limit=3)

            if relevant_memories:
                print(f"[FOUND] {len(relevant_memories)} relevant memories:")
                for i, mem in enumerate(relevant_memories, 1):
                    print(f"        {i}. Tick {mem.tick} at {mem.position}")
            else:
                print("[FOUND] No relevant memories (new situation)")

            # Build context for LLM
            context = self._build_context(observation, goal, relevant_memories)

            # Get decision from LLM
            decision = self.backend.generate(context)
            print(f"\n[DECIDE] {decision}")

            return decision

        def _build_context(
            self, observation: Observation, goal: str, memories: list[Observation]
        ) -> str:
            """Build prompt context with current state and relevant memories."""

            context_parts = []

            # Current state
            context_parts.append(f"Current State (Tick {observation.tick}):")
            context_parts.append(f"- Position: {observation.position}")
            context_parts.append(f"- Health: {observation.health}, Energy: {observation.energy}")

            if observation.nearby_resources:
                resources = [
                    f"{r.name} at distance {r.distance}" for r in observation.nearby_resources
                ]
                context_parts.append(f"- Resources: {', '.join(resources)}")

            if observation.nearby_hazards:
                hazards = [
                    f"{h.name} (damage {h.damage}) at distance {h.distance}"
                    for h in observation.nearby_hazards
                ]
                context_parts.append(f"- Hazards: {', '.join(hazards)}")

            if observation.inventory:
                items = [f"{item.name} x{item.quantity}" for item in observation.inventory]
                context_parts.append(f"- Inventory: {', '.join(items)}")

            # Goal
            context_parts.append(f"\nGoal: {goal}")

            # Relevant memories
            if memories:
                context_parts.append("\nRelevant Past Experiences:")
                for i, mem in enumerate(memories, 1):
                    context_parts.append(f"{i}. Tick {mem.tick} at {mem.position}")
                    if mem.nearby_resources:
                        res = [r.name for r in mem.nearby_resources]
                        context_parts.append(f"   Resources found: {', '.join(res)}")
                    if mem.nearby_hazards:
                        haz = [(h.name, h.damage) for h in mem.nearby_hazards]
                        context_parts.append(f"   Hazards: {haz}")

            return "\n".join(context_parts)

    # Initialize agent
    print("\nInitializing agent with LLM backend...")
    backend = MockLLMBackend()
    agent = RAGAgent("agent_001", backend)

    print("\n" + "=" * 70)
    print("SCENARIO 1: Learning to find food")
    print("=" * 70)

    # First experience: Finding berries
    obs1 = Observation(
        agent_id="agent_001",
        tick=10,
        position=(10.0, 0.0, 5.0),
        health=100.0,
        energy=90.0,
        nearby_resources=[
            ResourceInfo(name="berries", type="food", position=(11.0, 0.0, 5.0), distance=1.0)
        ],
    )
    agent.decide(obs1, "Find food to restore energy")

    # Second experience: Collecting berries
    obs2 = Observation(
        agent_id="agent_001",
        tick=15,
        position=(11.0, 0.0, 5.0),
        health=100.0,
        energy=95.0,  # Restored
        inventory=[ItemInfo(id="b1", name="berries", quantity=5)],
    )
    agent.decide(obs2, "Successfully collected food")

    print("\n" + "=" * 70)
    print("SCENARIO 2: Learning to avoid danger")
    print("=" * 70)

    # Experience: Encountering fire
    obs3 = Observation(
        agent_id="agent_001",
        tick=25,
        position=(20.0, 0.0, 10.0),
        health=100.0,
        energy=85.0,
        nearby_hazards=[
            HazardInfo(
                name="fire",
                type="environmental",
                position=(22.0, 0.0, 10.0),
                distance=2.0,
                damage=30.0,
            )
        ],
    )
    agent.decide(obs3, "Avoid hazards to maintain health")

    # Experience: Taking damage
    obs4 = Observation(
        agent_id="agent_001",
        tick=27,
        position=(22.0, 0.0, 10.0),
        health=70.0,  # Damaged!
        energy=80.0,
        nearby_hazards=[
            HazardInfo(
                name="fire",
                type="environmental",
                position=(22.0, 0.0, 10.0),
                distance=0.5,
                damage=30.0,
            )
        ],
    )
    agent.decide(obs4, "Took damage from hazard - learn from mistake")

    print("\n" + "=" * 70)
    print("SCENARIO 3: Finding water and materials")
    print("=" * 70)

    # Experience: Finding water
    obs5 = Observation(
        agent_id="agent_001",
        tick=35,
        position=(5.0, 0.0, 15.0),
        health=70.0,
        energy=70.0,
        nearby_resources=[
            ResourceInfo(name="water", type="liquid", position=(5.5, 0.0, 15.0), distance=0.5),
            ResourceInfo(name="stone", type="material", position=(6.0, 0.0, 15.0), distance=1.0),
        ],
    )
    agent.decide(obs5, "Find water and building materials")

    print("\n" + "=" * 70)
    print("SCENARIO 4: Using memory to make informed decisions")
    print("=" * 70)

    # New situation: Agent needs food again
    obs6 = Observation(
        agent_id="agent_001",
        tick=50,
        position=(8.0, 0.0, 3.0),
        health=65.0,
        energy=40.0,  # Low energy!
        inventory=[ItemInfo(id="s1", name="stone", quantity=2)],
    )
    decision = agent.decide(obs6, "Find food to restore low energy")

    # New situation: Agent encounters fire again
    obs7 = Observation(
        agent_id="agent_001",
        tick=60,
        position=(18.0, 0.0, 12.0),
        health=65.0,
        energy=50.0,
        nearby_hazards=[
            HazardInfo(
                name="fire",
                type="environmental",
                position=(20.0, 0.0, 12.0),
                distance=2.0,
                damage=30.0,
            )
        ],
    )
    decision = agent.decide(obs7, "Safely navigate around fire hazard")

    # New situation: Need water
    obs8 = Observation(
        agent_id="agent_001", tick=70, position=(3.0, 0.0, 12.0), health=60.0, energy=45.0
    )
    decision = agent.decide(obs8, "Find water source to drink")

    print("\n" + "=" * 70)
    print("MEMORY STATISTICS")
    print("=" * 70)
    print(f"Total observations stored: {len(agent.memory)}")
    print(f"\nFull memory summary:")
    print(agent.memory.summarize())

    print("\n" + "=" * 70)
    print("TESTING SEMANTIC SEARCH QUALITY")
    print("=" * 70)

    test_queries = [
        "Where did I successfully find food?",
        "What happened when I got close to fire?",
        "Where are water sources located?",
        "What resources have I collected?",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 70)
        results = agent.memory.retrieve(query=query, limit=2)
        if results:
            for i, obs in enumerate(results, 1):
                desc = f"Tick {obs.tick} at {obs.position} - Health: {obs.health}"
                print(f"  {i}. {desc}")
        else:
            print("  No relevant memories found")

    print("\n" + "=" * 70)
    print("[SUCCESS] RAG + LLM Agent simulation complete!")
    print("=" * 70)

    print("\nKey Insights:")
    print("1. Agent stores every observation automatically")
    print("2. When making decisions, agent queries relevant past experiences")
    print("3. LLM receives both current state AND relevant memories")
    print("4. Agent learns from mistakes (e.g., fire damage)")
    print("5. Agent recalls successful strategies (e.g., berry locations)")
    print("6. Semantic search finds relevant memories even with different wording")

except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
