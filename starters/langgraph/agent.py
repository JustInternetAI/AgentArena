"""
LangGraph-Powered Agent — Learn LangGraph by Building a Game Agent

This agent teaches you LangGraph's core concepts by building an AI agent
that plays Agent Arena scenarios:

1. StateGraph       — Define a graph of nodes connected by edges
2. Nodes            — Functions that read/write to shared state (messages)
3. Conditional edges — Route based on the LLM's output (tool call vs. text)
4. Tool binding     — Give the LLM structured tools it can call
5. State schema     — TypedDict that flows through the graph

How it works each tick:
1. Game sends an Observation (what the agent sees)
2. We format it into a HumanMessage for the LLM
3. The LangGraph agent graph runs: LLM sees context + tools → calls a tool
4. We extract the tool call and return it as a Decision
5. The game engine executes the action

This is YOUR code — modify the system prompt, swap to OpenAI, add memory,
or restructure the graph!

Learn more about LangGraph:
  https://langchain-ai.github.io/langgraph/
"""

import logging
import os
from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

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


# ---------------------------------------------------------------------------
# LangGraph State Schema
# ---------------------------------------------------------------------------
# LangGraph passes this TypedDict through every node in the graph.
# The ``messages`` key uses the ``add_messages`` reducer, which means
# each node *appends* messages rather than replacing the whole list.
# This is how LangGraph manages conversation history.

class AgentState(TypedDict):
    """State that flows through the LangGraph agent graph."""
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# LangGraph Adapter
# ---------------------------------------------------------------------------

class LangGraphAdapter(FrameworkAdapter):
    """
    LangGraph adapter using a ReAct-style StateGraph.

    The graph has two nodes:

    - **agent**: Calls the LLM with the current messages and tool definitions.
    - **tools**: A passthrough node (the game engine executes the real action).

    A conditional edge after the agent node checks:

    - If the LLM called a tool → route to ``tools`` → END
    - If no tool call → END

    Note: The graph routes ``tools → END`` (not ``tools → agent``). This
    means exactly one tool call per tick. In a standard ReAct agent, you'd
    loop back to the agent node for multi-step reasoning. In Agent Arena,
    each tick is one action, so we stop after one tool call.

    Customise:
    - ``SYSTEM_PROMPT`` (module-level) for personality / strategy
    - ``model`` for different LLM models
    - ``max_tokens`` for response length budget
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
        api_key: str | None = None,
    ):
        """
        Initialise the LangGraph adapter.

        Args:
            model: Model ID. Good options:
                - claude-sonnet-4-20250514 (fast, cheap — good default)
                - claude-opus-4-20250514  (most capable, slower)
                - claude-haiku-4-5-20251001 (fastest, cheapest)
            max_tokens: Maximum tokens for the LLM response.
            api_key: Anthropic API key. If None, reads ANTHROPIC_API_KEY
                from environment.
        """
        self.model_name = model
        self.max_tokens = max_tokens
        self.system_prompt = SYSTEM_PROMPT

        # Chain-of-thought trace for the debug viewer.
        # The SDK's debug system reads this via adapter.last_trace.
        self.last_trace: dict | None = None

        # --- Step 1: Create the LLM ------------------------------------------
        # LangGraph uses LangChain chat models. ChatAnthropic wraps the
        # Anthropic API with a standard interface that LangGraph understands.
        #
        # To use OpenAI instead:
        #   from langchain_openai import ChatOpenAI
        #   self.llm = ChatOpenAI(model="gpt-4o", ...)
        self.llm = ChatAnthropic(
            model=model,
            max_tokens=max_tokens,
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )

        # --- Step 2: Bind tools to the LLM -----------------------------------
        # LangGraph needs the LLM to know about available tools so it can
        # call them. ``bind_tools()`` attaches tool definitions to every
        # LLM call. We use our ToolSchema.to_openai_format() which produces
        # the OpenAI function calling format that LangChain understands.
        openai_tools = [t.to_openai_format() for t in self.get_action_tools()]
        self.llm_with_tools = self.llm.bind_tools(openai_tools)

        # --- Step 3: Build the graph ------------------------------------------
        self.graph = self._build_graph()

    def _build_graph(self):
        """
        Build the LangGraph agent graph.

        Graph structure::

            START → agent → should_continue? → tools → END
                                             ↘ END

        This is the classic **ReAct pattern** as a graph:

        1. **agent node**: LLM reads messages + tool definitions, responds
        2. **Conditional edge**: Did the LLM call a tool?
        3. **tools node**: Passthrough (game engine handles execution)
        4. **END**: Return the final state

        In a real multi-step agent, the ``tools`` node would execute the
        tool and feed results back to the ``agent`` node in a loop. In
        Agent Arena, the game engine executes actions, so we stop after
        capturing the tool call.
        """
        # Create a new graph with our state schema
        graph = StateGraph(AgentState)

        # --- Node 1: Agent ---------------------------------------------------
        # This node calls the LLM with the current messages. The LLM sees
        # the system prompt, observation context, and tool definitions,
        # then decides which tool to call (or responds with text).
        def agent_node(state: AgentState) -> dict:
            response = self.llm_with_tools.invoke(state["messages"])
            # Return the response as a new message to append to state
            return {"messages": [response]}

        # --- Node 2: Tools ---------------------------------------------------
        # In a standard LangGraph agent, this would be a ToolNode that
        # executes the tool and returns the result. In Agent Arena, the
        # game engine executes actions, so this is a passthrough.
        #
        # We still include this node to teach the ReAct graph structure.
        # When you add query tools (e.g., spatial memory lookups), you'd
        # replace this with a real ToolNode that executes those queries.
        def tools_node(state: AgentState) -> dict:
            return {"messages": []}  # No-op: game engine handles execution

        # --- Register nodes ---------------------------------------------------
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tools_node)

        # --- Set entry point --------------------------------------------------
        graph.set_entry_point("agent")

        # --- Conditional edge: should we continue? ----------------------------
        # After the agent node, check if the LLM called a tool.
        # If yes → route to tools node. If no → END.
        def should_continue(state: AgentState) -> str:
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        graph.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", END: END},
        )

        # --- After tools, stop ------------------------------------------------
        # In a multi-step ReAct agent, you'd route back to "agent" here.
        # We route to END because Agent Arena uses one action per tick.
        graph.add_edge("tools", END)

        # --- Compile the graph ------------------------------------------------
        # Compiling optimises the graph and validates the structure.
        return graph.compile()

    def decide(self, obs: Observation) -> Decision:
        """
        Make a decision using the LangGraph agent graph.

        1. Format observation → HumanMessage
        2. Invoke graph with system prompt + observation
        3. Extract tool call from AIMessage → Decision
        4. Fall back to observation-based logic on any failure
        """
        # --- Build prompt -----------------------------------------------------
        obs_text = self.format_observation(obs)

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

        # --- Invoke graph -----------------------------------------------------
        try:
            result = self.graph.invoke({
                "messages": [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=obs_text),
                ]
            })

            # Find the AIMessage (the LLM's response) in the result
            ai_message = self._find_ai_message(result["messages"])

            if ai_message and ai_message.tool_calls:
                # LLM called a tool — extract it as our Decision
                tool_call = ai_message.tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # The "explore" tool is synthetic — the game only
                # understands move_to. We translate here.
                if tool_name == "explore":
                    decision = self._resolve_explore(obs)
                else:
                    decision = Decision(
                        tool=tool_name,
                        params=tool_args,
                        reasoning=self._extract_reasoning(ai_message),
                    )

                trace["parse_method"] = "tool_call"
                trace["decision"] = {
                    "tool": decision.tool,
                    "params": decision.params,
                    "reasoning": decision.reasoning,
                }

                # Extract token usage if available
                usage = getattr(ai_message, "usage_metadata", None)
                if usage:
                    trace["tokens_used"] = (
                        usage.get("input_tokens", 0)
                        + usage.get("output_tokens", 0)
                    )

                self.last_trace = trace
                return decision

            # LLM returned text but no tool call
            trace["parse_method"] = "fallback_no_tool_call"
            if ai_message:
                content = ai_message.content
                trace["llm_raw_output"] = (
                    content if isinstance(content, str) else str(content)
                )
            logger.warning("LLM did not call a tool, using fallback")

        except Exception as e:
            logger.error(f"LangGraph error: {e}")
            trace["parse_method"] = "error"

        # --- Fallback ---------------------------------------------------------
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
    def _extract_reasoning(ai_message: AIMessage) -> str:
        """Extract text content from the AIMessage to use as reasoning."""
        content = ai_message.content
        if isinstance(content, str):
            return content if content else "LangGraph decision"
        # LangChain sometimes returns content as a list of blocks
        if isinstance(content, list):
            texts = [
                block["text"] if isinstance(block, dict) else str(block)
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
                or isinstance(block, str)
            ]
            return " ".join(texts) if texts else "LangGraph decision"
        return "LangGraph decision"

    @staticmethod
    def _find_ai_message(messages: list) -> AIMessage | None:
        """Find the last AIMessage in the message list."""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg
        return None
