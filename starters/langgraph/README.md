# LangGraph Starter — Learn LangGraph by Building a Game Agent

This starter teaches you **LangGraph** by building an AI agent that plays Agent Arena scenarios.

**Key idea:** "Want to learn LangGraph? Build an AI agent that plays a game."

## What You'll Learn

- **Graph construction** — StateGraph, adding nodes, connecting edges
- **State schema** — TypedDict with message reducers (`add_messages`)
- **Tool binding** — Giving the LLM structured tools via `bind_tools()`
- **Conditional routing** — Branching the graph based on LLM output
- **ReAct pattern** — The observe-think-act loop as a graph
- **Message types** — SystemMessage, HumanMessage, AIMessage

## Prerequisites

1. An **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com)
2. Python 3.11+
3. Agent Arena game (Godot) running

## Quick Start

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the agent
python run.py

# 4. In Godot: open scenes/foraging.tscn -> F5 -> SPACE
```

Your agent will start making decisions using a LangGraph agent graph!

## Files

| File | What it does |
|------|-------------|
| `agent.py` | `LangGraphAdapter` — builds the agent graph, invokes it, extracts decisions |
| `run.py` | Entry point — parses args, creates adapter, starts server |
| `requirements.txt` | Dependencies (agent-arena-sdk, langgraph, langchain-anthropic) |

## How It Works

Each game tick:

```
Godot sends Observation (what the agent sees)
    |
LangGraphAdapter.format_observation() -> text context
    |
Graph invoked with [SystemMessage, HumanMessage]
    |
    v
+-------+    tool call?    +-------+
| agent | ----YES--------> | tools | --> END
|       | ----NO---------> END     |
+-------+                  +-------+
    |                          |
    LLM reads context          No-op passthrough
    + tool definitions         (game executes action)
    |
    v
Extract tool call from AIMessage -> Decision
    |
Decision sent back to Godot
```

### The Key Concepts

#### 1. StateGraph — The Foundation

Everything in LangGraph starts with a `StateGraph`. It defines what data flows through the graph (the "state") and how nodes transform it:

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

graph = StateGraph(AgentState)
```

The `add_messages` annotation is a **reducer** — it tells LangGraph to *append* new messages rather than replacing the list. This is how conversation history builds up.

#### 2. Nodes — Processing Steps

Nodes are functions that take the current state and return updates:

```python
def agent_node(state: AgentState) -> dict:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}  # Appended via add_messages

graph.add_node("agent", agent_node)
```

#### 3. Conditional Edges — Decision Routing

After a node runs, conditional edges inspect the state and choose the next node:

```python
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"  # LLM called a tool
    return END          # LLM just returned text

graph.add_conditional_edges("agent", should_continue, ...)
```

#### 4. Tool Binding — Structured Actions

`bind_tools()` attaches tool definitions to the LLM so it can call them with typed parameters:

```python
tools = [schema.to_openai_format() for schema in self.get_action_tools()]
llm_with_tools = llm.bind_tools(tools)
```

The LLM responds with an `AIMessage` containing `tool_calls`:

```python
ai_message.tool_calls[0]
# {"name": "move_to", "args": {"target_position": [10.0, 0.0, 5.0]}}
```

#### 5. Single-Action vs Multi-Step

In a standard ReAct agent, the `tools` node executes the tool and routes back to `agent` for another round. In Agent Arena, each tick is one action, so:

```python
graph.add_edge("tools", END)  # Stop after one tool call
# vs.
# graph.add_edge("tools", "agent")  # Loop for multi-step reasoning
```

## Customization

### Change the System Prompt

Edit `SYSTEM_PROMPT` at the top of `agent.py`. Try:
- Adding personality ("You are a cautious agent that avoids all risk")
- Changing strategy ("Always explore before collecting")
- Adding domain knowledge ("Fire hazards deal 10 damage per tick")

### Change the Model

```bash
python run.py --model claude-haiku-4-5-20251001  # Fastest, cheapest
python run.py --model claude-sonnet-4-20250514   # Balanced (default)
python run.py --model claude-opus-4-20250514     # Most capable
```

### Swap to OpenAI

1. Update `requirements.txt`:
   ```
   langchain-openai>=0.3.0  # Replace langchain-anthropic
   ```

2. In `agent.py`, change the import and LLM creation:
   ```python
   from langchain_openai import ChatOpenAI

   self.llm = ChatOpenAI(
       model="gpt-4o",
       max_tokens=max_tokens,
       api_key=api_key or os.environ.get("OPENAI_API_KEY"),
   )
   ```

Everything else stays the same — LangGraph abstracts the LLM provider.

### Add Memory (Checkpointing)

LangGraph has built-in memory via checkpointers. Add state persistence across ticks:

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
self.graph = self._build_graph()  # Returns compiled graph
# Recompile with checkpointer:
self.graph = graph.compile(checkpointer=checkpointer)

# Invoke with a thread_id to maintain conversation history:
result = self.graph.invoke(
    {"messages": [HumanMessage(content=obs_text)]},
    config={"configurable": {"thread_id": "agent-1"}},
)
```

### Add Multi-Step Reasoning

To let the agent reason across multiple tool calls before acting (e.g., query memory then decide), change the graph to loop:

```python
# Instead of: graph.add_edge("tools", END)
graph.add_edge("tools", "agent")  # Loop back for another round
```

Then add "query" tools (spatial memory, episode memory) alongside the action tools. The agent will call query tools to gather info, then call an action tool to act.

### Restructure the Graph

Add new nodes for preprocessing, memory, or planning:

```python
graph.add_node("preprocess", preprocess_node)   # Clean observation
graph.add_node("memory", memory_node)            # Query past experiences
graph.add_node("agent", agent_node)              # LLM decision
graph.add_node("tools", tools_node)              # Execute tools

graph.set_entry_point("preprocess")
graph.add_edge("preprocess", "memory")
graph.add_edge("memory", "agent")
# ... conditional edges for agent -> tools
```

## Cost Estimation

Each tick costs approximately (using Anthropic via LangChain):
- **Haiku**: ~0.1 cent (500 input + 100 output tokens)
- **Sonnet**: ~0.5 cent
- **Opus**: ~2.5 cents

A typical foraging run (100 ticks) costs ~$0.10 with Sonnet.

## Debugging

### Enable Debug Viewer

```bash
python run.py --debug
# Open http://127.0.0.1:5000/debug in your browser
```

### View Traces

The adapter records each decision in `self.last_trace` with:
- System prompt sent
- Observation context sent
- Tokens used
- Parse method (tool_call, fallback, error)
- Final decision

### LangSmith Integration

LangGraph integrates natively with [LangSmith](https://smith.langchain.com/) for tracing:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=ls-...
python run.py
```

Every graph invocation will appear in the LangSmith dashboard with full execution traces.

### Common Issues

**"LLM did not call a tool"** — The LLM sometimes returns text without calling a tool. The adapter falls back to observation-based logic. Try making the system prompt more directive.

**High latency** — Each tick requires an API round-trip. Use Haiku for faster responses.

**"ANTHROPIC_API_KEY not set"** — Export your API key: `export ANTHROPIC_API_KEY=sk-ant-...`

## Comparison with Claude Starter

| Feature | Claude Starter | LangGraph Starter |
|---------|---------------|-------------------|
| Approach | Direct Anthropic API | Graph-based agent |
| State management | Manual | LangGraph state + reducers |
| Tool format | Anthropic native | OpenAI function calling |
| Extensibility | Modify `decide()` | Add nodes and edges |
| Memory | Manual implementation | Built-in checkpointers |
| Multi-step reasoning | Not built-in | Native (loop tools -> agent) |
| Observability | Custom traces | LangSmith integration |
| LLM provider | Anthropic only | Any LangChain chat model |

## Next Steps

- Add **checkpointing** for memory across ticks
- Add **query tools** (spatial memory, episode memory) as non-terminal reasoning steps
- Enable **multi-step reasoning** by routing `tools -> agent` in the graph
- Try the **`create_react_agent`** shortcut: `from langgraph.prebuilt import create_react_agent`
- Read the [LangGraph docs](https://langchain-ai.github.io/langgraph/) to learn more
