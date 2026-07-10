from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.services.tools.upload_tool import upload_document
from app.services.tools.status_tool import get_document_status
from app.services.tools.search_tool import search_knowledge_base
from app.config.settings import get_settings

s = get_settings()
def get_agent():
     tools = [
         upload_document,
         get_document_status,
         search_knowledge_base
     ]
     agent = create_react_agent(
        llm=ChatOpenAI(
            model=s.SILICON_MODEL,
            api_key=s.SILICON_API_KEY,
            base_url=s.SILICON_BASE_URL,
            streaming=True,
            callbacks=[],
        ),
        tools=tools,
        prompt=PromptTemplate.from_template(
            """
            你是一个企业知识库助手。使用以下工具来回答用户问题：
            
            {tools}
            
            使用以下格式：
            Question: 用户的问题
            Thought: 你应该思考要做什么
            Action: 要使用的工具名(从[{tool_names}]中选择)
            Action Input: 工具的输入
            Observation: 工具返回的结果
            ... (这个 Thought/Action/Action Input/Observation 可以重复多次)
            Thought: 我现在知道最终答案了
            Final Answer: 最终答案
            
            开始！
            Question: {input}
            Thought: {agent_scratchpad}
"""
        )
,
    )
     return AgentExecutor(agent=agent,tools=tools,handle_parsing_errors=True)