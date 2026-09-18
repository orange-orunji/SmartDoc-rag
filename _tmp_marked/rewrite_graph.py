from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import START,END
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.config.settings import get_settings

s = get_settings()

_llm = ChatOpenAI(
    model=s.SILICON_MODEL,
    api_key=s.SILICON_API_KEY,
    base_url=s.SILICON_BASE_URL,
    streaming=True,
    temperature=0.3,
    callbacks=[],
)

_tool = []


_llm_with_tools = _llm.bind_tools(_tool)

_ACTION_WORDS = []
_MEMORY_WORDS = []


class AgentState(MessagesState):
    retrieval_context: str = ""
    web_context: str = ""

def search_or_none(state: AgentState) -> str:
    if state["retrieval_context"] == "":
        return "web_search"
    return "agent"

def web_search(state: AgentState) -> dict:
    pass

def action_pass_node(state: AgentState) -> str:
    q = state["messages"][-1].content
    if any([k in q for k in _ACTION_WORDS]):
        return "skip"
    if any(k in q for k in _MEMORY_WORDS):
        return "skip"
    return "retrieve"

def retrieve(state: AgentState) -> dict:
    return {"retrieval_context": "".join(["文档片段1","文档片段2"])}

def router(state: AgentState) -> str:
    if getattr(state["messages"][-1], "tool_calls", None):
        return "tools"
    return "END"

def recover(state: AgentState) :
    return{
        "web_context": "",
        "retrieval_context": ""
    }

def call_model(state: AgentState) -> dict:
    question = state["messages"][-1].content
    response = _llm_with_tools.invoke(question)
    return {"messages": [response]}



builder = StateGraph(AgentState)
builder.add_node("web_search", web_search)
builder.add_node("recover",recover)
builder.add_node("agent",call_model)
builder.add_node("retrieve",retrieve)
builder.add_node("tools",ToolNode(_tool))

builder.add_edge(START,"recover")
builder.add_conditional_edges("recover",action_pass_node,{"retrieve":"retrieve","skip":"agent"})
builder.add_conditional_edges("retrieve",search_or_none,{"agent":"agent","web_search":"web_search"})
builder.add_conditional_edges("agent",router,{"END":END,"tools":"tools"})
builder.add_edge("tools","agent")
builder.add_edge("web_search","agent")

graph = builder.compile()


def run_agent():
    print(sorted(graph.get_graph().nodes.keys()))
    print(graph.invoke({"messages": [HumanMessage(content="测试")]}))

if __name__ == "__main__":
    run_agent()
