from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import START ,END
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.config.settings import get_settings

s = get_settings()
_llm = ChatOpenAI(model=s.SILICON_MODEL, api_key=s.SILICON_API_KEY, base_url=s.SILICON_BASE_URL, streaming=True,
                temperature=0.3, callbacks=[], )

_tool = []

_MEMORY_WORD = []
_ACTION_WORD = []
_PASS_WORD = []

_llm_with_tool = _llm.bind_tools(_tool)

class AgentState(MessagesState):
    retrieval_context: str = ""
    web_context: str = ""

def action_pass_node(state: AgentState) -> str:
    q = state["messages"][-1].content
    if any(k in q for k in _ACTION_WORD):
        return "skip"
    if any(k in q for k in _MEMORY_WORD):
        return "skip"
    if any(k in q for k in _PASS_WORD):
        return "skip"
    return "retrieve"

def retrieve_node(state: AgentState) -> dict:
    return {
        "retrieval_context": "\n\n".join(["片段1","片段2"])
    }


def router(state: AgentState) -> str:
    if getattr(state["messages"][-1], "tool_calls", None):
        return "tools"
    return "END"

def recover(state: AgentState) -> dict:
    return {
        "retrieval_context": "",
        "web_context": ""
    }

def web_search_node(state: AgentState) -> dict:
    return{
        "web_context": "\n\n".join(["网络搜索片段1","网络片段2"])
    }

def retrieve_is_none(state: AgentState) -> str:
    if state["retrieval_context"] == "":
        return "web"
    return "agent"

def call_model(state: AgentState):
    question = state["messages"][-1].content
    result = _llm_with_tool.invoke(question)
    return {"messages": [result]}


builder = StateGraph(AgentState)
builder.add_node("recover",recover)
builder.add_node("retrieve",retrieve_node)
builder.add_node("web",web_search_node)
builder.add_node("agent",call_model)
builder.add_node("tools",ToolNode(_tool))

builder.add_edge(START,"recover")
builder.add_conditional_edges("recover", action_pass_node, {"retrieve": "retrieve", "skip": "agent"})
builder.add_conditional_edges("retrieve",retrieve_is_none,{"web":"web","agent":"agent"})
builder.add_edge("web","agent")
builder.add_conditional_edges("agent", router, {"tools": "tools", "END":END})
builder.add_edge("tools","agent")


graph = builder.compile()

if __name__ == '__main__':
    print(graph.invoke({"messages": [HumanMessage(content="你好")]}))
