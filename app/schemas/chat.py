from datetime import datetime

from pydantic import BaseModel

class ChatRequest(BaseModel):
    message : str