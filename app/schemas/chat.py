from typing import Optional

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


class RenameRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100, description="新的会话名称")

# ── 响应模型 ──

class HistoryMessage(BaseModel):
    """单条对话历史"""
    role: str       # "human" | "assistant"
    content: str


class HistoryResponse(BaseModel):
    """对话历史列表"""
    messages: list[HistoryMessage]


class SessionListResponse(BaseModel):
    """会话 ID 列表"""
    sessions: list[str]
    session_meta: dict[str, str] = {}   # 会话名 → 最后更新时间（YYYY-MM-DD HH:MM）
    titles: dict[str, str] = {}         # 会话 ID → 显示标题（自动生成 / 手动重命名）


class SessionActionResponse(BaseModel):
    """会话删除/重命名结果"""
    code: int
    message: str
    data: Optional[dict] = None

class ResumeRequest(BaseModel):
    """"""
    session_id: str
    decision: bool