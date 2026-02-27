"""
Claude-Powered Agent — Using Anthropic's Claude with Native Tool Use

This agent uses Claude's tool_use feature for structured decision making.
Instead of generating JSON text and parsing it (like the LLM starter),
Claude directly calls tools with typed parameters — no parsing errors.

How it works:
1. Each tick, the game sends an Observation (what the agent sees)
2. We format that into text context for Claude
3. Claude reads the context and calls an action tool (move_to, collect, etc.)
4. We extract the tool call and return it as a Decision

This is YOUR code — modify the system prompt, change the model,
add memory, or customize the observation formatting!

Learn more about Anthropic tool use:
  https://docs.anthropic.com/en/docs/build-with-claude/tool-use
"""

import logging
import os

from anthropic import Anthropic

from agent_arena_sdk import Decision, Observation
from agent_arena_sdk.adapters import FrameworkAdapter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt — edit this to change your agent's personality and strategy!
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an AI agent in a 3D simulation world (50m x 50m).
Your goal is to collect resources, avoid hazards, and complete objectives.

IMPORTANT CONSTRAINTS:
- You have LIMITED VISIBILITY (~10 unit radius). You can only see nearby things.
- World boundaries are roughly -25 to +25 on both X and Z axes.
- Each tool call is ONE action per tick. Choose wisely.

STRATEGY:
- If a hazard is within 3 units, move away immediately (survival first).
- If resources are nearby, move toward the closest one to collect it.
- If you have crafting materials and are near a station, craft items.
- If nothing is visible, explore to discover new areas.
- Read the objective and prioritize actions that make progress.

Crafting recipes (must be near the correct station):
- torch: 1 wood + 1 stone (workbench)
- meal: 2 berry (workbench)
- shelter: 3 wood + 2 stone (anvil)

Use the provided tools to take actions. Each tool call ends your turn.\
"""


class ClaudeAdapter(FrameworkAdapter):
    """
    Anthropic Claude adapter using native tool_use.

    Per tick this adapter:
    1. Formats the observation into text context
    2. Sends it to Claude with action tool definitions
    3. Claude calls a tool → we return that as the Decision

    Customise:
    - ``SYSTEM_PROMPT`` (module-level) for personality / strategy
    - ``model`` for different Claude models
    - ``max_tokens`` for response length budget
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
        api_key: str | None = None,
    ):
        """
        Initialise the Claude adapter.

        Args:
            model: Anthropic model ID. Good options:
                - claude-sonnet-4-20250514 (fast, cheap — good default)
                - claude-opus-4-20250514  (most capable, slower)
                - claude-haiku-4-5-20251001 (fastest, cheapest)
            max_tokens: Maximum tokens for Claude's response.
            api_key: Anthropic API key. If None, reads ANTHROPIC_API_KEY
                from environment.
        """
        self.model = model
        self.max_tokens = max_tokens
        self.client = Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.system_prompt = SYSTEM_PROMPT

        # Chain-of-thought trace for the debug viewer.
        # The SDK's debug system reads this via adapter.last_trace.
        self.last_trace: dict | None = None

    def decide(self, obs: Observation) -> Decision:
        """
        Make a decision using Claude's tool_use.

        1. Format observation → text context
        2. Call Claude with tools
        3. Extract tool_use block → Decision
        4. Fall back to observation-based logic on any failure
        """
        # --- Build prompt -------------------------------------------------
        obs_text = self.format_observation(obs)

        # Convert our ToolSchema objects to Anthropic's format:
        #   {"name": ..., "description": ..., "input_schema": {...}}
        tools = [t.to_anthropic_format() for t in self.get_action_tools()]

        # Trace dict for the debug viewer
        trace: dict = {
            "system_prompt": self.system_prompt,
            "user_prompt": obs_text,
            "llm_raw_output": None,
            "tokens_used": 0,
            "finish_reason": None,
            "parse_method": None,
            "decision": None,
        }

        # --- Call Claude --------------------------------------------------
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": obs_text}],
                tools=tools,
            )

            trace["tokens_used"] = (
                response.usage.input_tokens + response.usage.output_tokens
            )
            trace["finish_reason"] = response.stop_reason

            # --- Extract tool call ----------------------------------------
            # Claude returns content blocks. We look for a tool_use block.
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # The "explore" tool is synthetic — Claude calls it, but
                    # the game only understands move_to. We translate here.
                    if tool_name == "explore":
                        decision = self._resolve_explore(obs)
                    else:
                        decision = Decision(
                            tool=tool_name,
                            params=tool_input,
                            reasoning=self._extract_reasoning(response),
                        )

                    trace["parse_method"] = "tool_use"
                    trace["decision"] = {
                        "tool": decision.tool,
                        "params": decision.params,
                        "reasoning": decision.reasoning,
                    }
                    self.last_trace = trace
                    return decision

            # Claude returned text but no tool call
            trace["llm_raw_output"] = self._extract_all_text(response)
            trace["parse_method"] = "fallback_no_tool_use"
            logger.warning("Claude did not call a tool, using fallback")

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            trace["parse_method"] = "error"

        # --- Fallback -----------------------------------------------------
        decision = self.fallback_decision(obs)
        trace["decision"] = {
            "tool": decision.tool,
            "params": decision.params,
            "reasoning": decision.reasoning,
        }
        self.last_trace = trace
        return decision

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_explore(self, obs: Observation) -> Decision:
        """Translate the synthetic 'explore' tool into a concrete move_to."""
        if obs.exploration and obs.exploration.explore_targets:
            target = obs.exploration.explore_targets[0]
            return Decision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Exploring {target.direction}",
            )
        # No exploration data — move in +X as a heuristic
        px, py, pz = obs.position
        return Decision(
            tool="move_to",
            params={"target_position": [px + 10.0, py, pz]},
            reasoning="Exploring (no targets available)",
        )

    @staticmethod
    def _extract_reasoning(response) -> str:
        """Pull text blocks from the response to use as reasoning."""
        texts = [
            block.text
            for block in response.content
            if block.type == "text"
        ]
        return " ".join(texts) if texts else "Claude decision"

    @staticmethod
    def _extract_all_text(response) -> str:
        """Concatenate all text content blocks."""
        return " ".join(
            block.text for block in response.content if block.type == "text"
        )
