"""
LangGraph state machine for AeroSwarm worker agent.

Nodes:
  think  → call LLM with current task state
  act    → execute the chosen tool
  check  → decide: continue working or mark done
"""

import os
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agent.tools import list_dir_tool, read_file_tool, run_shell_tool, write_file_tool


class AgentState(TypedDict):
    agent_id: str
    task_description: str
    scope_dir: str
    messages: Annotated[list[BaseMessage], add_messages]
    completed: bool
    last_output: str


TOOLS = [read_file_tool, write_file_tool, list_dir_tool, run_shell_tool]


def _build_llm() -> ChatOpenAI:
    provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
    model = os.environ.get("LLM_MODEL", "gpt-4o").strip()

    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in the agent container")
        return ChatOpenAI(
            model=model,
            temperature=0.1,
            api_key=api_key,
            base_url=os.environ.get(
                "GEMINI_OPENAI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            ),
            default_headers={"x-goog-api-client": "aeroswarm-oai/0.1.0"},
        ).bind_tools(TOOLS)

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured in the agent container")
    return ChatOpenAI(model=model, temperature=0.1, api_key=api_key).bind_tools(TOOLS)


def build_graph() -> StateGraph:
    llm = _build_llm()

    def think(state: AgentState) -> dict:
        from langchain_core.messages import HumanMessage, SystemMessage

        system = SystemMessage(content="""You are an expert software engineer.
Use the available tools to complete the assigned task.
You MUST only read and write files inside the allowed scope directory.
When the task is fully complete, output exactly: TASK_COMPLETE""")
        task_prompt = HumanMessage(
            content=(
                f"Task: {state['task_description']}\n"
                f"Allowed scope directory: {state['scope_dir']}\n"
                "Inspect the existing code first, then make the required changes."
            )
        )

        messages = [system, task_prompt] + state["messages"]
        response = llm.invoke(messages)
        return {
            "messages": [response],
            "last_output": str(response.content)[:200],
        }

    def act(state: AgentState) -> dict:
        """Execute tool calls from the last message."""
        from langchain_core.messages import ToolMessage

        last_msg = state["messages"][-1]
        tool_results = []

        tool_map = {t.name: t for t in TOOLS}

        if hasattr(last_msg, "tool_calls"):
            for tool_call in last_msg.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                if tool_name not in tool_map:
                    result = f"ERROR: unknown tool '{tool_name}'"
                else:
                    try:
                        result = tool_map[tool_name].invoke(tool_args)
                    except Exception as exc:
                        result = f"ERROR: {exc}"

                tool_results.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

        return {
            "messages": tool_results,
            "last_output": f"Executed {len(tool_results)} tool(s)",
        }

    def check(state: AgentState) -> str:
        """Route: done if LLM said TASK_COMPLETE, else loop."""
        last_msg = state["messages"][-1]
        content = getattr(last_msg, "content", "")
        if isinstance(content, str) and "TASK_COMPLETE" in content:
            return "done"
        # If there are pending tool calls, go to act; otherwise think again
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "act"
        return "think"

    graph = StateGraph(AgentState)
    graph.add_node("think", think)
    graph.add_node("act", act)

    graph.set_entry_point("think")
    graph.add_conditional_edges("think", check, {"done": END, "act": "act", "think": "think"})
    graph.add_edge("act", "think")

    return graph.compile()
