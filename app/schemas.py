from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    clinic_id: str = Field(..., description="ID of the selected clinic (e.g. glow-skin, bright-dental)")
    user_id: str = Field(..., description="Unique user or patient session identifier")
    message: str = Field(..., description="User chat message content")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant reply message")
    clinic_id: str
    user_id: str
    timestamp: Optional[str] = None
    model_used: Optional[str] = None

