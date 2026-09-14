from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState ,START , END
from langgraph.prebuilt import  ToolNode
from langchain_openai import ChatOpenAI
from functools import lru_cache

import re

from app.config.settings import get_settings
from app.services.hyde import adaptive_retrieve
from app.services.tools.upload_tool import upload_document
from app.services.tools.status_tool import get_document_status,generate_report,convert_format,send_email
from app.services.tools.search_tool import search_knowledge_base
from app.services.tools.delete_tool import delete_document

s = get_settings()
_tools = [
         upload_document,
         get_document_status,
         search_knowledge_base,
         generate_report,
         convert_format,
         send_email,
         delete_document,
     ]
_llm = ChatOpenAI(
            model=s.SILICON_MODEL,
            api_key=s.SILICON_API_KEY,
            base_url=s.SILICON_BASE_URL,
            streaming=True,
            callbacks=[],
        ).bind_tools(_tools)

_SYSTEM_PROMPT = """你是一个企业知识库助手，帮助用户从已上传的文档中查找信息。
## 核心原则（必须严格遵守）
**所有用户提问，若已有【知识库检索结果】上下文，直接基于它回答；仅当上下文不足以回答时，才调用 search_knowledge_base 补充。**
不得未经检索就直接凭训练知识回答。

## 唯一例外（可以不调 search_knowledge_base）
- 用户说"谢谢"、"好的"等纯社交用语
- 数学计算（如"1+1等于几"）
- 用户明确说"不用查文档，直接告诉我"

## 其他工具
- 用户说"上传"、"帮我存"、"加进知识库" → 调用 upload_document
- 用户问"知识库有什么"、"有多少文档" → 调用 get_document_status
- 用户要求生成报告时调用 -> generate_report
- 用户要求转换文件格式调用 -> convert_format
- 用户要求将文件/消息进行邮件发送调用 -> send_email
- 用户要求删除文件 -> delete_document


## 回答要求
- 检索到相关内容时：优先引用文档内容，标注"根据知识库文档："
- 检索结果为空时：回答"知识库中未找到相关内容"，然后可补充通用知识并标注"根据通用知识："
- 知识库内容与通用知识冲突时：以知识库为准
- 输出 Markdown 表格时：表格与表格、表格与段落之间必须用空行分隔；每个表格行必须以 | 开头和结尾，不得跨行
- 引用知识库内容时在句末标注（来源：文档名）；回答末尾列'引用来源'小节
"""

_checkpointer = None
_GREET_WORDS = ["你好","hello","hi","谢谢","你是谁"]
_ACTION_WORDS = ["删除", "删掉", "移除", "清理", "去掉", "上传", "存入",
                 "入库", "保存", "导出", "有哪些文档", "多少文档","多少个文档","文档数"]
_ACTION_PATTERNS = [
    r"发.{0,3}邮件",
    r"生成.{0,3}报告",
    r"转.{0,3}(Word|word|格式)",
    r"发{0,3}邮件"
]
# 注入检查点，用于保存中间状态，防止无状态的图被缓存
def set_checkpointer(cp):
    global _checkpointer
    _checkpointer = cp

def get_checkpointer():
    return _checkpointer

class AgentState(MessagesState):
    retrieval_context: str = ""


def router(state: AgentState) -> str:
    q = str(state["messages"][-1].content)
    if any(k in q for k in _GREET_WORDS):
        return "skip"
    if any(k in q for k in _ACTION_WORDS) or \
       any(re.search(p,q) for p in _ACTION_PATTERNS):  # 动作类 → skip
        return "skip"
    return "retrieve"

def retrieve(state: AgentState) -> dict:
    question = state["messages"][-1].content
    docs = adaptive_retrieve(question)
    docs_text =  "\n\n".join(
        f"【来源: {d.metadata.get('source')} \n{d.page_content}】" for d in docs
    )
    return {"retrieval_context": docs_text}


async def call_model(state: AgentState) -> dict:
    system = _SYSTEM_PROMPT
    ctx = state.get("retrieval_context","")
    if ctx:
        system += f"\n\n【知识库检索结果】\n{ctx}"
    msgs = [SystemMessage(content=system)] + state["messages"]
    response = await _llm.ainvoke(msgs)
    return {"messages": [response]}


def continues(state: AgentState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "END"

@lru_cache(maxsize=None)
def get_agent():
    builder = StateGraph(AgentState)

    builder.add_node("retrieve", retrieve)
    builder.add_node("agent",call_model)
    builder.add_node("tools",ToolNode(_tools))

    builder.add_conditional_edges(START, router , {"retrieve": "retrieve", "skip": "agent"})
    builder.add_edge("retrieve","agent")
    builder.add_conditional_edges("agent",continues,{"tools":"tools","END":END})
    builder.add_edge("tools","agent")

    return builder.compile(checkpointer=_checkpointer)