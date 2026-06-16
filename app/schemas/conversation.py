from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.message import MessageResponse

class ConversationCreate(BaseModel):
    user_id: str
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True
