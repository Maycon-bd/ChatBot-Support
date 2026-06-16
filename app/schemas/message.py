from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageCreate(BaseModel):
    content: str
    image_base64: Optional[str] = None  # Optional base64 screenshot of the error

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    image_url: Optional[str] = None
    is_action: bool
    ticket_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
