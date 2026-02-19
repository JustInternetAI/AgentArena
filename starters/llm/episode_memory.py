"""
Episode-Aware Long-Term Memory Manager for the LLM Agent

Wraps LongTermMemory (FAISS + sentence-transformers) with:
- Episode lifecycle detection (tick resets)
- Episode summary generation and storage
- Key event detection and immediate storage
- Query construction from observations
- Memory hygiene (cap, dedup)
- Persistence management

This is YOUR code - you can modify thresholds, storage logic, and query strategy!
"""

import logging
import math
import sys
from pathlib import Path
from typing import Any

# Ensure python/ is on the path for long_term_memory_module imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

from long_term_memory_module import LongTermMemory
from agent_arena_sdk import Observation

logger = logging.getLogger(__name__)


class EpisodeMemoryManager:
    """
    Manages long-term memory across episodes for the LLM agent.

    Provides:
    - Episode boundary detection (tick resets)
    - RAG retrieval before each decision
    - Key event storage during episodes
    - Episode summary storage at episode end
    - Deduplication and memory cap enforcement
    - Disk persistence

    Example:
        manager = EpisodeMemoryManager(persist_dir="data/memory")

        # Each tick in decide():
        if manager.check_episode_boundary(obs):
            manager.on_episode_end(last_obs)
            manager.on_episode_start(obs)

        manager.check_key_events(obs)
        memories = manager.query_relevant_memories(obs)
        prompt_text = manager.format_memories_for_prompt(memories)
    """

    # --- Configuration constants (tune these!) ---
    MAX_MEMORIES = 500
    DEDUP_THRESHOLD = 0.95  # Cosine similarity above which memories are considered duplicates
    RESOURCE_CLUSTER_RADIUS = 5.0
    RESOURCE_CLUSTER_MIN = 3
    SIGNIFICANT_DAMAGE_THRESHOLD = 20.0
    QUERY_RESULTS_K = 3
    QUERY_SIMILARITY_THRESHOLD = 0.3
    QUERY_EVERY_N_TICKS = 5  # Only re-query RAG every N ticks for performance

    def __init__(self, persist_dir: str | None = None):
        """
        Initialize the episode memory manager.

        Args:
            persist_dir: Directory for saving memory files.
                         Defaults to starters/llm/data/memory/
        """
        if persist_dir is None:
            persist_dir = str(Path(__file__).parent / "data" / "memory")

        self.persist_path = str(Path(persist_dir) / "agent_ltm.faiss")

        # Initialize LongTermMemory with FlatIP for cosine similarity
        # (needed for meaningful threshold-based dedup and retrieval)
        self.ltm = LongTermMemory(
            embedding_model="all-MiniLM-L6-v2",
            index_type="FlatIP",
            persist_path=self.persist_path,
        )

        # Force the embedding model to CPU so it doesn't compete with the
        # LLM for GPU memory. Without this, SentenceTransformer grabs CUDA
        # by default and can starve the LLM of VRAM.
        try:
            self.ltm.encoder = self.ltm.encoder.to("cpu")
            logger.info("Embedding model pinned to CPU (GPU reserved for LLM)")
        except Exception:
            pass  # Non-critical — works fine either way

        # Try to load existing memories from disk
        try:
            self.ltm.load()
            logger.info(f"Loaded {len(self.ltm)} existing long-term memories")
        except FileNotFoundError:
            logger.info("No existing memories found, starting fresh")

        # Episode tracking state
        self.episode_number: int = 0
        self._prev_tick: int = -1
        self._episode_start_health: float = 100.0
        self._episode_resources_collected: int = 0
        self._episode_hazard_types_seen: set[str] = set()
        self._episode_total_damage: float = 0.0
        self._episode_max_tick: int = 0
        self._prev_health: float = 100.0
        self._last_inventory_count: int = 0

        # Key event tracking (persists across episodes)
        self._known_hazard_types: set[str] = set()

        # RAG query cache
        self._cached_memories: list[dict[str, Any]] = []
        self._cache_tick: int = -1

    # ------------------------------------------------------------------ #
    #  Episode Lifecycle
    # ------------------------------------------------------------------ #

    def check_episode_boundary(self, obs: Observation) -> bool:
        """
        Detect whether a new episode has started by checking for tick reset.

        Returns True if the tick number dropped (new episode started).
        """
        is_new_episode = self._prev_tick > 0 and obs.tick < self._prev_tick
        self._prev_tick = obs.tick
        return is_new_episode

    def on_episode_start(self, obs: Observation) -> None:
        """Reset per-episode tracking for a new episode."""
        self.episode_number += 1
        self._episode_start_health = obs.health
        self._episode_resources_collected = 0
        self._episode_hazard_types_seen = set()
        self._episode_total_damage = 0.0
        self._episode_max_tick = obs.tick
        self._prev_health = obs.health
        self._last_inventory_count = (
            sum(item.quantity for item in obs.inventory) if obs.inventory else 0
        )
        # Invalidate RAG cache for new episode
        self._cached_memories = []
        self._cache_tick = -1
        logger.info(f"Episode {self.episode_number} started")

    def on_episode_end(self, last_obs: Observation) -> None:
        """Summarize the completed episode and store learnings in long-term memory."""
        # Build and store episode summary
        summary = self._build_episode_summary(last_obs)
        summary_meta = {
            "type": "episode_summary",
            "episode": self.episode_number,
            "ticks": self._episode_max_tick,
            "final_health": last_obs.health,
            "resources_collected": self._episode_resources_collected,
            "damage_taken": self._episode_total_damage,
        }
        self._store_if_novel(summary, summary_meta)

        # Extract and store strategy learnings
        learnings = self._extract_learnings(last_obs)
        for learning in learnings:
            learn_meta = {
                "type": "learning",
                "episode": self.episode_number,
                "category": learning["category"],
            }
            self._store_if_novel(learning["text"], learn_meta)

        # Enforce memory cap and persist
        self._enforce_memory_cap()
        self.save()
        logger.info(
            f"Episode {self.episode_number} ended. "
            f"Stored summary + {len(learnings)} learnings. "
            f"Total memories: {len(self.ltm)}"
        )

    # ------------------------------------------------------------------ #
    #  Key Event Detection (called every tick)
    # ------------------------------------------------------------------ #

    def check_key_events(self, obs: Observation) -> list[str]:
        """
        Check for key events worth storing immediately.

        Called every tick. Detects:
        - New hazard type discovered
        - Resource cluster found
        - Significant damage taken

        Returns list of event description strings (for trace logging).
        """
        events: list[str] = []
        self._episode_max_tick = max(self._episode_max_tick, obs.tick)

        # 1. New hazard type discovered
        if obs.nearby_hazards:
            for h in obs.nearby_hazards:
                if h.type not in self._known_hazard_types:
                    self._known_hazard_types.add(h.type)
                    self._episode_hazard_types_seen.add(h.type)
                    text = (
                        f"Discovered hazard type '{h.type}' ({h.name}) "
                        f"at position [{h.position[0]:.1f}, {h.position[1]:.1f}, {h.position[2]:.1f}], "
                        f"damage={h.damage}. Distance was {h.distance:.1f}."
                    )
                    meta = {
                        "type": "hazard_discovery",
                        "episode": self.episode_number,
                        "hazard_type": h.type,
                        "position": list(h.position),
                    }
                    self._store_if_novel(text, meta)
                    events.append(text)

        # 2. Resource cluster (3+ resources within radius of each other)
        if len(obs.nearby_resources) >= self.RESOURCE_CLUSTER_MIN:
            cluster_text = self._detect_resource_cluster(obs)
            if cluster_text:
                meta = {
                    "type": "resource_cluster",
                    "episode": self.episode_number,
                    "position": list(obs.position),
                }
                self._store_if_novel(cluster_text, meta)
                events.append(cluster_text)

        # 3. Significant damage taken (>threshold HP drop in one tick)
        damage = self._prev_health - obs.health
        if damage > self.SIGNIFICANT_DAMAGE_THRESHOLD:
            self._episode_total_damage += damage
            text = (
                f"Took {damage:.0f} damage at position "
                f"[{obs.position[0]:.1f}, {obs.position[1]:.1f}, {obs.position[2]:.1f}] "
                f"(health dropped from {self._prev_health:.0f} to {obs.health:.0f})."
            )
            if obs.nearby_hazards:
                closest = min(obs.nearby_hazards, key=lambda h: h.distance)
                text += (
                    f" Nearest hazard: {closest.name} ({closest.type}) "
                    f"at dist {closest.distance:.1f}."
                )
            meta = {
                "type": "damage_event",
                "episode": self.episode_number,
                "damage": damage,
                "position": list(obs.position),
            }
            self._store_if_novel(text, meta)
            events.append(text)
        elif damage > 0:
            self._episode_total_damage += damage

        # Track resource collection via inventory changes
        current_inv = sum(item.quantity for item in obs.inventory) if obs.inventory else 0
        if current_inv > self._last_inventory_count:
            self._episode_resources_collected += current_inv - self._last_inventory_count
        self._last_inventory_count = current_inv

        self._prev_health = obs.health
        return events

    # ------------------------------------------------------------------ #
    #  Memory Retrieval
    # ------------------------------------------------------------------ #

    def query_relevant_memories(self, obs: Observation) -> list[dict[str, Any]]:
        """
        Query RAG for memories relevant to the current situation.

        Results are cached for QUERY_EVERY_N_TICKS ticks to amortize
        the embedding cost.
        """
        # Return cached results if still fresh
        if (
            obs.tick - self._cache_tick < self.QUERY_EVERY_N_TICKS
            and self._cached_memories
        ):
            return self._cached_memories

        if len(self.ltm) == 0:
            return []

        query = self._build_situation_query(obs)
        results = self.ltm.query_memory(
            query,
            k=self.QUERY_RESULTS_K,
            threshold=self.QUERY_SIMILARITY_THRESHOLD,
        )
        self._cached_memories = results
        self._cache_tick = obs.tick
        return results

    def format_memories_for_prompt(self, memories: list[dict[str, Any]]) -> str:
        """Format retrieved memories into a string for the LLM prompt."""
        if not memories:
            return "No relevant past experiences."

        lines = []
        for i, mem in enumerate(memories, 1):
            score = mem.get("score", 0)
            episode = mem.get("metadata", {}).get("episode", "?")
            lines.append(f"  {i}. [Ep.{episode}, relevance={score:.2f}] {mem['text']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Internal Helpers
    # ------------------------------------------------------------------ #

    def _build_situation_query(self, obs: Observation) -> str:
        """Build a natural-language query from the current observation."""
        parts = [
            f"Agent at position [{obs.position[0]:.1f}, {obs.position[1]:.1f}, {obs.position[2]:.1f}]"
        ]
        parts.append(f"health={obs.health:.0f} energy={obs.energy:.0f}")

        if obs.nearby_resources:
            types = sorted(set(r.type for r in obs.nearby_resources))
            parts.append(f"nearby resources: {', '.join(types)}")

        if obs.nearby_hazards:
            types = sorted(set(h.type for h in obs.nearby_hazards))
            parts.append(f"nearby hazards: {', '.join(types)}")

        if obs.health < 50:
            parts.append("low health, need to be careful")

        return ". ".join(parts)

    def _build_episode_summary(self, last_obs: Observation) -> str:
        """Build a text summary of the completed episode."""
        hazards_str = ", ".join(self._episode_hazard_types_seen) or "none"
        return (
            f"Episode {self.episode_number} summary: "
            f"Lasted {self._episode_max_tick} ticks. "
            f"Collected {self._episode_resources_collected} resources. "
            f"Took {self._episode_total_damage:.0f} total damage. "
            f"Final health: {last_obs.health:.0f}. "
            f"Hazard types encountered: {hazards_str}."
        )

    def _extract_learnings(self, last_obs: Observation) -> list[dict[str, str]]:
        """Extract key learnings from episode statistics."""
        learnings: list[dict[str, str]] = []

        if self._episode_total_damage > 50:
            learnings.append({
                "category": "strategy",
                "text": (
                    f"In episode {self.episode_number}, took heavy damage "
                    f"({self._episode_total_damage:.0f} total). "
                    f"Should be more cautious around hazards."
                ),
            })

        if self._episode_resources_collected > 5:
            learnings.append({
                "category": "strategy",
                "text": (
                    f"Episode {self.episode_number} was productive: "
                    f"collected {self._episode_resources_collected} resources in "
                    f"{self._episode_max_tick} ticks."
                ),
            })

        if last_obs.health <= 0:
            learnings.append({
                "category": "survival",
                "text": (
                    f"Died in episode {self.episode_number} at position "
                    f"[{last_obs.position[0]:.1f}, {last_obs.position[1]:.1f}, {last_obs.position[2]:.1f}] "
                    f"after {self._episode_max_tick} ticks. "
                    f"Need to prioritize survival over resource collection."
                ),
            })

        return learnings

    def _detect_resource_cluster(self, obs: Observation) -> str | None:
        """Detect if 3+ resources are clustered within RESOURCE_CLUSTER_RADIUS."""
        resources = obs.nearby_resources
        for i, r1 in enumerate(resources):
            cluster = [r1]
            for j, r2 in enumerate(resources):
                if i == j:
                    continue
                dist = math.sqrt(
                    sum((a - b) ** 2 for a, b in zip(r1.position, r2.position))
                )
                if dist < self.RESOURCE_CLUSTER_RADIUS:
                    cluster.append(r2)
            if len(cluster) >= self.RESOURCE_CLUSTER_MIN:
                types = sorted(set(r.type for r in cluster))
                center = [
                    sum(r.position[k] for r in cluster) / len(cluster)
                    for k in range(3)
                ]
                return (
                    f"Found resource cluster of {len(cluster)} resources "
                    f"({', '.join(types)}) near position "
                    f"[{center[0]:.1f}, {center[1]:.1f}, {center[2]:.1f}]."
                )
        return None

    def _store_if_novel(self, text: str, metadata: dict[str, Any]) -> str | None:
        """Store memory only if not too similar to existing memories (dedup)."""
        if len(self.ltm) > 0:
            similar = self.ltm.query_memory(text, k=1, threshold=self.DEDUP_THRESHOLD)
            if similar:
                logger.debug(
                    f"Skipping duplicate memory (score={similar[0]['score']:.3f}): "
                    f"{text[:60]}..."
                )
                return None

        memory_id = self.ltm.store_memory(text, metadata)
        return memory_id

    def _enforce_memory_cap(self) -> None:
        """Remove oldest memories if over the cap."""
        if len(self.ltm) <= self.MAX_MEMORIES:
            return

        all_mems = self.ltm.get_all_memories()
        all_mems.sort(key=lambda m: m.get("metadata", {}).get("episode", 0))

        to_remove = len(self.ltm) - self.MAX_MEMORIES
        keep = all_mems[to_remove:]

        self.ltm.clear_memories()
        for mem in keep:
            self.ltm.store_memory(mem["text"], mem["metadata"])

        logger.info(f"Memory cap enforced: removed {to_remove} oldest memories")

    # ------------------------------------------------------------------ #
    #  Persistence
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        """Persist memories to disk."""
        try:
            self.ltm.save()
            logger.info(f"Saved {len(self.ltm)} memories to {self.persist_path}")
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")

    @property
    def memory_count(self) -> int:
        """Number of memories currently stored."""
        return len(self.ltm)
