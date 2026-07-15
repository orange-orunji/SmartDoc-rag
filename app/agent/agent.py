from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from functools import lru_cache

from app.config.settings import get_settings
from app.services.tools.upload_tool import upload_document
from app.services.tools.status_tool import get_document_status,generate_report,convert_format
from app.services.tools.search_tool import search_knowledge_base

s = get_settings()
_tools = [
         upload_document,
         get_document_status,
         search_knowledge_base,
         generate_report,
         convert_format,
     ]
_llm = ChatOpenAI(
            model=s.SILICON_MODEL,
            api_key=s.SILICON_API_KEY,
            base_url=s.SILICON_BASE_URL,
            streaming=True,
            callbacks=[],
        )
_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个企业知识库助手，帮助用户从已上传的文档中查找信息。

    ## 核心原则（必须严格遵守）
    **所有用户提问，默认先调用 search_knowledge_base 检索知识库，再基于检索结果回答。**
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
    
    ## 回答要求
    - 检索到相关内容时：优先引用文档内容，标注"根据知识库文档："
    - 检索结果为空时：回答"知识库中未找到相关内容"，然后可补充通用知识并标注"根据通用知识："
    - 知识库内容与通用知识冲突时：以知识库为准"""),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

@lru_cache(maxsize=None)
def get_agent():
     agent = create_tool_calling_agent(
        llm=_llm,
        tools=_tools,
        prompt=_prompt,
    )
     return AgentExecutor(agent=agent,tools=_tools,handle_parsing_errors=True)