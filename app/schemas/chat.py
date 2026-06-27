
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


class RenameRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100, description="新的会话名称")