from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    extra_field: int


def node(state: State):
    print("node 收到的 state:", state)
    return {
        "messages": [AIMessage("您好")],
        "extra_field": 1,
    }


graph = StateGraph(State)
graph.add_node("my_node", node)
graph.add_edge(START, "my_node")
graph.add_edge("my_node", END)

graph_builder = graph.compile()

# 不太懂还，依旧阿，加三
if __name__ == "__main__":
    result = graph_builder.invoke({"messages": [], "extra_field": 0})
    print("最终 state:", result)

