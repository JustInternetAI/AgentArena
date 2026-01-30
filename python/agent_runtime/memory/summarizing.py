"""
Summarizing memory implementation using LLM compression.
"""

from typing import TYPE_CHECKING, Any

from .base import AgentMemory

if TYPE_CHECKING:
    from ..schemas import Observation


class SummarizingMemory(AgentMemory):
    """
    LLM-compressed memory for long episodes.

    Uses an LLM to compress observations into a running summary when
    the buffer fills up. Keeps:
    - A compressed summary of older observations
    - A small window of recent raw observations

    This allows agents to maintain context over long episodes without
    exceeding token limits.

    Example:
        backend = SomeLLMBackend()
        memory = SummarizingMemory(
            backend=backend,
            buffer_capacity=20,
            compression_trigger=15
        )

        # As observations are stored, periodic compression happens automatically
        for obs in many_observations:
            memory.store(obs)

        # Summary includes both compressed history and recent observations
        context = memory.summarize()
    """

    def __init__(
        self,
        backend: Any,
        buffer_capacity: int = 20,
        compression_trigger: int = 15,
    ):
        """
        Initialize summarizing memory.

        Args:
            backend: LLM backend with generate() method
            buffer_capacity: Maximum observations before forcing compression
            compression_trigger: Number of observations that trigger compression
        """
        if buffer_capacity < 1:
            raise ValueError("Buffer capacity must be at least 1")
        if compression_trigger < 1:
            raise ValueError("Compression trigger must be at least 1")
        if compression_trigger > buffer_capacity:
            raise ValueError("Compression trigger must be <= buffer capacity")

        self.backend = backend
        self.buffer_capacity = buffer_capacity
        self.compression_trigger = compression_trigger

        self._summary: str = ""
        self._buffer: list[Observation] = []
        self._total_observations: int = 0

    def store(self, observation: "Observation") -> None:
        """
        Store an observation in memory.

        Automatically compresses if buffer reaches trigger threshold.

        Args:
            observation: The observation to store
        """
        self._buffer.append(observation)
        self._total_observations += 1

        # Trigger compression if buffer is getting full
        if len(self._buffer) >= self.compression_trigger:
            self._compress()

    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """
        Retrieve observations from memory.

        Note: Only returns observations in the recent buffer (compressed
        observations are not retrievable as raw Observations).

        Args:
            query: Ignored (kept for interface compatibility)
            limit: Maximum number of observations to return (most recent)

        Returns:
            List of recent observations, most recent first
        """
        if limit is None:
            return list(reversed(self._buffer))
        else:
            return list(reversed(self._buffer[-limit:]))

    def summarize(self) -> str:
        """
        Create a text summary of memory contents for LLM context.

        Returns:
            String with compressed summary + recent observations
        """
        lines = []

        # Include compressed summary if it exists
        if self._summary:
            lines.append("=== Compressed Memory Summary ===")
            lines.append(self._summary)
            lines.append("")

        # Include recent observations
        if self._buffer:
            lines.append(f"=== Recent Observations ({len(self._buffer)} most recent) ===")
            for obs in reversed(self._buffer):
                lines.append(f"\n[Tick {obs.tick}]")
                lines.append(f"  Position: {obs.position}")

                if obs.visible_entities:
                    entities_str = ", ".join(f"{e.type}:{e.id}" for e in obs.visible_entities[:3])
                    lines.append(f"  Entities: {entities_str}")

                if obs.nearby_resources:
                    resources_str = ", ".join(r.name for r in obs.nearby_resources[:3])
                    lines.append(f"  Resources: {resources_str}")

                if obs.nearby_hazards:
                    hazards_str = ", ".join(h.name for h in obs.nearby_hazards[:3])
                    lines.append(f"  Hazards: {hazards_str}")

                if obs.inventory:
                    items_str = ", ".join(f"{item.name}x{item.quantity}" for item in obs.inventory)
                    lines.append(f"  Inventory: {items_str}")

                lines.append(f"  Health: {obs.health:.0f}, Energy: {obs.energy:.0f}")
        else:
            if not self._summary:
                lines.append("No observations in memory.")

        return "\n".join(lines)

    def clear(self) -> None:
        """
        Clear all stored memories.
        """
        self._summary = ""
        self._buffer.clear()
        self._total_observations = 0

    def _compress(self) -> None:
        """
        Compress buffer observations into summary using LLM.

        Internal method called automatically when buffer fills.
        """
        if not self._buffer:
            return

        # Build prompt for compression
        prompt_lines = [
            "Summarize the following agent observations into a concise narrative.",
            "Focus on: significant events, discoveries, state changes, and patterns.",
            "Be brief but preserve important details.",
            "",
        ]

        if self._summary:
            prompt_lines.append("Previous summary:")
            prompt_lines.append(self._summary)
            prompt_lines.append("")

        prompt_lines.append("New observations to integrate:")
        for obs in self._buffer:
            prompt_lines.append(
                f"Tick {obs.tick}: pos={obs.position}, "
                f"resources={len(obs.nearby_resources)}, "
                f"hazards={len(obs.nearby_hazards)}, "
                f"health={obs.health:.0f}"
            )

        prompt = "\n".join(prompt_lines)

        # Get compressed summary from LLM
        try:
            if hasattr(self.backend, "generate"):
                self._summary = self.backend.generate(prompt)
            else:
                # Fallback: simple text compression if backend doesn't have generate()
                self._summary = self._fallback_compress()
        except Exception:
            # If LLM fails, use fallback
            self._summary = self._fallback_compress()

        # Keep only most recent observations in buffer
        keep_count = self.buffer_capacity - self.compression_trigger
        if keep_count > 0:
            self._buffer = self._buffer[-keep_count:]
        else:
            self._buffer.clear()

    def _fallback_compress(self) -> str:
        """
        Fallback compression without LLM.

        Creates a simple summary of key statistics.

        Returns:
            Simple text summary
        """
        if not self._buffer:
            return self._summary

        lines = []
        if self._summary:
            lines.append(self._summary)

        start_tick = self._buffer[0].tick
        end_tick = self._buffer[-1].tick

        # Count occurrences
        resources_seen: set[str] = set()
        hazards_seen: set[str] = set()
        max_health = max(obs.health for obs in self._buffer)
        min_health = min(obs.health for obs in self._buffer)

        for obs in self._buffer:
            resources_seen.update(r.name for r in obs.nearby_resources)
            hazards_seen.update(h.name for h in obs.nearby_hazards)

        summary_parts = [
            f"Ticks {start_tick}-{end_tick}: ",
            f"Observed {len(resources_seen)} resource types, ",
            f"{len(hazards_seen)} hazard types. ",
            f"Health range: {min_health:.0f}-{max_health:.0f}.",
        ]

        lines.append("".join(summary_parts))
        return " ".join(lines)

    def __len__(self) -> int:
        """
        Get number of observations in memory.

        Returns:
            Total count including compressed observations
        """
        return self._total_observations
