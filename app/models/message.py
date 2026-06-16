import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)  # URL or base64 string if the user sent an error screenshot
    
    # Flags indicating escalation
    is_action = Column(Boolean, default=False)  # True if the LLM action node opened a ticket
    ticket_id = Column(String, nullable=True)  # Simulated ticket ID if escalated

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
