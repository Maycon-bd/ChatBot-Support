import logging
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.database import get_db
from app.services.agent_service import AgentService
from app.models.tenant import Tenant
from app.models.user import User
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationResponse, ConversationDetailResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

class MessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    user_id: str
    content: str
    image_base64: Optional[str] = None  # Imagem de erro opcional codificada em Base64

class MessageResponseSchema(BaseModel):
    conversation_id: str
    response: str
    is_action: bool
    ticket_id: Optional[str] = None
    retrieved_context: List[str] = []
    token_usage: Optional[Dict[str, Any]] = None

@router.post("/message", response_model=MessageResponseSchema)
def send_message(
    payload: MessageRequest,
    x_tenant_id: str = Header("quantum_corp", alias="X-Tenant-ID", description="ID do Tenant para isolamento dos dados"),
    db: Session = Depends(get_db)
):
    """
    Envia uma mensagem de texto e/ou imagem de erro para o agente de suporte inteligente (LangGraph).
    Retorna a resposta da IA e informações sobre escalação (chamados humanos).
    """
    # 1. Garante que o Tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == x_tenant_id).first()
    if not tenant:
        logger.info(f"Tenant '{x_tenant_id}' não cadastrado. Criando automaticamente.")
        tenant = Tenant(id=x_tenant_id, name=f"Tenant Autogerado ({x_tenant_id})")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    # 2. Garante que o Usuário existe no Tenant
    user = db.query(User).filter(User.id == payload.user_id, User.tenant_id == x_tenant_id).first()
    if not user:
        logger.info(f"Usuário '{payload.user_id}' não cadastrado para o tenant '{x_tenant_id}'. Criando automaticamente.")
        user = User(id=payload.user_id, tenant_id=x_tenant_id, name=f"User {payload.user_id[:8]}", email=f"user_{payload.user_id[:8]}@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Cria uma nova conversa se não fornecida
    conversation_id = payload.conversation_id
    if not conversation_id:
        conversation = Conversation(tenant_id=x_tenant_id, user_id=payload.user_id, title=f"Atendimento {payload.content[:20]}...")
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        conversation_id = conversation.id
        logger.info(f"Criada nova conversa ID: {conversation_id} para o usuário {payload.user_id}.")
    else:
        # Verifica se a conversa pertence ao tenant correto
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == x_tenant_id
        ).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conversa não localizada ou pertence a outro Tenant."
            )

    # 4. Executa o Agente LangGraph
    try:
        agent_service = AgentService()
        result = agent_service.run_agent(
            db=db,
            conversation_id=conversation_id,
            tenant_id=x_tenant_id,
            current_query=payload.content,
            image_base64=payload.image_base64
        )
        return {
            "conversation_id": conversation_id,
            "response": result["response"],
            "is_action": result["is_action"],
            "ticket_id": result["ticket_id"],
            "retrieved_context": result["retrieved_context"],
            "token_usage": result.get("token_usage")
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro ao executar agente de chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no processamento da mensagem pelo agente: {str(e)}"
        )


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    x_tenant_id: str = Header("quantum_corp", alias="X-Tenant-ID"),
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de todas as conversas do tenant ativo, garantindo o isolamento.
    """
    conversations = db.query(Conversation).filter(Conversation.tenant_id == x_tenant_id).all()
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    x_tenant_id: str = Header("quantum_corp", alias="X-Tenant-ID"),
    db: Session = Depends(get_db)
):
    """
    Retorna o histórico detalhado de mensagens de uma conversa específica, garantindo o isolamento de tenant.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == x_tenant_id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada ou não pertence a este Tenant."
        )
    return conversation
