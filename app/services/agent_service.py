import uuid
import logging
import base64
from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict
from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.config import settings
from app.services.qdrant_service import QdrantService
from app.models.conversation import Conversation
from app.models.message import Message

logger = logging.getLogger(__name__)

def get_text_llm(temperature: float = 0) -> Any:
    """Retorna o modelo de texto configurado (Groq com fallback para Gemini)."""
    if settings.GROQ_API_KEY:
        try:
            logger.info(f"Instanciando ChatGroq com o modelo {settings.GROQ_MODEL}...")
            return ChatGroq(model=settings.GROQ_MODEL, groq_api_key=settings.GROQ_API_KEY, temperature=temperature)
        except Exception as e:
            logger.warning(f"Erro ao instanciar ChatGroq: {str(e)}. Utilizando fallback para Gemini.")
    
    logger.info(f"Instanciando ChatGoogleGenerativeAI com o modelo {settings.GEMINI_MODEL}...")
    return ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, api_key=settings.GEMINI_API_KEY, temperature=temperature)

# 1. Definição do Estado do Grafo

# Limite da janela de contexto do modelo Gemini (tokens de entrada)
GEMINI_CONTEXT_WINDOW = 1_048_576
# Limiar de alerta: avisa quando >80% da janela de contexto for consumida
TOKEN_ALERT_THRESHOLD = 0.80

def validate_input_guardrails(query: str) -> Optional[str]:
    """Valida se a entrada contém injeções de prompt ou dados sensíveis."""
    q_lower = query.lower()
    
    # 1. Dados Sensíveis e Senhas
    sensitive_patterns = ["senha", "password", "credenciais", "credentials", "token api", "chave secreta", "senha do admin", "secret"]
    if any(p in q_lower for p in sensitive_patterns):
        return "Desculpe, não posso processar solicitações relacionadas a dados sensíveis, senhas ou credenciais por motivos de segurança."
        
    # 2. Injeção de Prompt
    explicit_injections = [
        "ignore as regras", "ignore as instruções", "revelar prompt", "system prompt",
        "ignore as diretrizes", "ignore previous"
    ]
    if any(p in q_lower for p in explicit_injections):
        return "Desculpe, mas não posso processar essa solicitação devido às diretrizes de segurança do sistema. Como posso ajudar com o ERP?"
        
    # 3. Palavras Ofensivas
    offensive_words = ["idiota", "burro", "inútil", "merda", "foda", "caralho", "porra", "stupid"]
    if any(p in q_lower for p in offensive_words):
        return "Por favor, mantenha o respeito. Como posso te ajudar com o Odoo ERP?"
        
    return None

class AgentState(TypedDict):
    messages: List[Dict[str, Any]]       # Histórico de conversas formatado
    current_query: str                  # Pergunta atual do usuário
    tenant_id: str                      # Tenant ID (Isolamento rígido)
    image_base64: Optional[str]         # Imagem em base64 (se enviada)
    image_context: Optional[str]        # Texto/erro extraído da imagem
    retrieved_context: List[str]        # Contextos retornados pelo Qdrant
    response: Optional[str]             # Resposta final gerada
    is_action: bool                     # Indica se abriu chamado técnico
    ticket_id: Optional[str]            # ID do ticket gerado
    token_usage: Optional[Dict[str, Any]]  # Metadados de uso de tokens do LLM


# 2. Definição do Roteador Inteligente
def router_edge(state: AgentState) -> str:
    """Decide se direciona para processamento de imagem, RAG ou Ação de Chamado."""
    # Se houver imagem, obrigatoriamente vai para o Vision Node
    if state.get("image_base64"):
        logger.info("Roteador: Imagem detectada. Direcionando para Vision Node.")
        return "vision"
    
    # Classifica a intenção usando o LLM configurado
    llm = get_text_llm(temperature=0)
    
    classification_prompt = (
        "Classifique a intenção da mensagem do usuário no suporte de TI.\n"
        "Responda APENAS com a palavra 'TICKET' se o usuário deseja explicitamente abrir um chamado/ticket de suporte, falar com um atendente humano, ou se expressa frustração extrema solicitando escalação.\n"
        "Responda APENAS com a palavra 'SUPPORT' se o usuário estiver fazendo uma pergunta sobre como usar o sistema, resolvendo um problema técnico, ou buscando instruções nos manuais.\n\n"
        f"Mensagem do usuário: '{state['current_query']}'\n"
        "Intenção:"
    )
    
    try:
        res = llm.invoke([HumanMessage(content=classification_prompt)])
        intent = res.content.strip().upper()
        if "TICKET" in intent:
            logger.info("Roteador: Intenção de abertura de ticket detectada.")
            return "action"
    except Exception as e:
        logger.error(f"Erro ao classificar intenção via LLM no roteador: {str(e)}")
        # Fallback de busca de termos manuais
        q = state["current_query"].lower()
        ticket_triggers = ["abrir chamado", "abrir ticket", "suporte humano", "falar com humano", "escalar", "criar chamado", "abrir ticket"]
        if any(trigger in q for trigger in ticket_triggers):
            logger.info("Roteador: Intenção detectada via gatilhos manuais.")
            return "action"
            
    logger.info("Roteador: Direcionando para RAG Node.")
    return "rag"


# 3. Nós do Grafo
def vision_node(state: AgentState) -> Dict[str, Any]:
    """Processa o print de erro em base64 para extrair o texto do erro."""
    logger.info("Vision Node: Analisando print de erro...")
    llm = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, api_key=settings.GEMINI_API_KEY, temperature=0)
    
    message = HumanMessage(
        content=[
            {
                "type": "text", 
                "text": "Você é um especialista em suporte técnico de TI. Analise este print de erro. Extraia todas as mensagens de erro de texto visíveis, descreva brevemente qual parece ser o problema técnico e sugira termos/palavras-chave para pesquisar na base de conhecimento. Retorne isso de forma concisa."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{state['image_base64']}"
                }
            }
        ]
    )
    
    try:
        res = llm.invoke([message])
        error_description = res.content
        logger.info(f"Vision Node: Contexto extraído com sucesso: {error_description[:100]}...")
        return {
            "image_context": error_description
        }
    except Exception as e:
        logger.error(f"Erro ao processar imagem no Vision Node: {str(e)}")
        return {
            "image_context": "Erro ao tentar ler o print de erro enviado."
        }


def rag_node(state: AgentState) -> Dict[str, Any]:
    """Busca o manual técnico no Qdrant filtrando por tenant e gera a resposta."""
    logger.info(f"RAG Node: Iniciando busca de contexto para o Tenant: {state['tenant_id']}...")
    qdrant_service = QdrantService()
    
    # Se tiver contexto de imagem, nós o adicionamos na consulta técnica
    query_to_search = state["current_query"]
    if state.get("image_context"):
        query_to_search = f"{query_to_search}\nErro extraído da imagem: {state['image_context']}"
        
    # Executa a busca híbrida com isolamento estrito de tenant_id
    results = qdrant_service.hybrid_search(
        query=query_to_search,
        tenant_id=state["tenant_id"],
        top_k=4
    )
    
    context_chunks = [r["page_content"] for r in results]
    
    # Constrói o Prompt de Sistema com o contexto técnico recuperado
    system_prompt = (
        "Você é um Assistente de Suporte de Nível 1 especializado. Seu objetivo é ajudar a resolver a dúvida ou problema do usuário.\n"
        "Responda à dúvida baseando-se EXCLUSIVAMENTE nos documentos de contexto fornecidos. Seja claro, conciso e instrutivo.\n"
        "Se os documentos não contiverem a informação necessária para resolver o problema, responda educadamente que não encontrou "
        "esta informação na base de conhecimento e pergunte se ele gostaria de abrir um chamado técnico com o suporte humano.\n"
        "NÃO invente respostas fora do contexto abaixo.\n\n"
        "=== DOCUMENTOS DE CONTEXTO ===\n"
        + "\n\n".join(context_chunks) + "\n"
        "=============================="
    )
    
    # Prepara as mensagens para o LLM
    api_messages = [SystemMessage(content=system_prompt)]
    
    # Adiciona o histórico filtrado do State (últimas 5 interações)
    for msg in state.get("messages", []):
        if msg["role"] == "user":
            api_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            api_messages.append(AIMessage(content=msg["content"]))
            
    # Adiciona a mensagem atual
    api_messages.append(HumanMessage(content=state["current_query"]))
    
    # Executa o LLM para geração da resposta final
    llm = get_text_llm(temperature=0.2)
    response = llm.invoke(api_messages)

    # Captura metadados de uso de tokens agnóstico de provedor
    token_usage = None
    
    # Determina dinamicamente a janela de contexto
    # Groq Llama 3.3 tem 128k, Gemini tem 1M
    context_window = GEMINI_CONTEXT_WINDOW
    if settings.GROQ_API_KEY and "llama" in settings.GROQ_MODEL.lower():
        context_window = 128_000

    usage = getattr(response, "usage_metadata", None)
    input_tokens = 0
    output_tokens = 0
    
    if usage:
        input_tokens  = getattr(usage, "input_tokens",  0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
    elif hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
        token_usage_meta = response.response_metadata["token_usage"]
        input_tokens = token_usage_meta.get("prompt_tokens", 0)
        output_tokens = token_usage_meta.get("completion_tokens", 0)
        
    if input_tokens > 0 or output_tokens > 0:
        total_tokens  = input_tokens + output_tokens
        usage_ratio   = input_tokens / context_window if context_window else 0
        token_usage = {
            "input_tokens":       input_tokens,
            "output_tokens":      output_tokens,
            "total_tokens":       total_tokens,
            "context_window":     context_window,
            "usage_ratio":        round(usage_ratio, 4),
            "alert":              usage_ratio >= TOKEN_ALERT_THRESHOLD,
        }
        logger.info(
            f"Token usage — input: {input_tokens}, output: {output_tokens}, "
            f"total: {total_tokens}, ratio: {usage_ratio:.2%}"
        )

    return {
        "retrieved_context": context_chunks,
        "response": response.content,
        "token_usage": token_usage
    }


def action_node(state: AgentState) -> Dict[str, Any]:
    """Nó acionado para abertura de chamados técnicos simulada."""
    logger.info("Action Node: Simulando integração com sistema de tickets...")
    ticket_id = f"TK-{uuid.uuid4().hex[:6].upper()}"
    
    response_msg = (
        f"Com certeza! Compreendi sua solicitação e criei o chamado **{ticket_id}** "
        f"para que nossa equipe técnica de Nível 2 avalie o seu caso. "
        f"Retornaremos o contato em breve."
    )
    
    return {
        "response": response_msg,
        "is_action": True,
        "ticket_id": ticket_id
    }


class AgentService:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Registra os nós no grafo
        workflow.add_node("vision", vision_node)
        workflow.add_node("rag", rag_node)
        workflow.add_node("action", action_node)
        
        # Ponto de entrada condicional (Roteador)
        workflow.set_conditional_entry_point(
            router_edge,
            {
                "vision": "vision",
                "rag": "rag",
                "action": "action"
            }
        )
        
        # Conexão entre os nós
        workflow.add_edge("vision", "rag")  # Após a visão, busca na base de conhecimento
        workflow.add_edge("rag", END)
        workflow.add_edge("action", END)
        
        return workflow.compile()

    def run_agent(
        self,
        db: Session,
        conversation_id: str,
        tenant_id: str,
        current_query: str,
        image_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Carrega o histórico de mensagens da conversa, realiza o gerenciamento de memória
        (janela de contexto + sumarização), executa o grafo e persiste a interação no banco relacional.
        """
        # 1. Recupera a conversa e valida isolamento de tenant_id
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id
        ).first()
        
        if not conversation:
            raise ValueError(f"Conversa com ID '{conversation_id}' não localizada ou acesso não autorizado.")

        # 1.5 Guardrails de Entrada
        guardrail_violation = validate_input_guardrails(current_query)
        if guardrail_violation:
            logger.warning(f"Guardrail acionado para a query: {current_query}")
            
            user_message = Message(
                conversation_id=conversation_id,
                role="user",
                content=current_query,
                image_url=image_base64
            )
            db.add(user_message)
            
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=guardrail_violation,
                is_action=False
            )
            db.add(assistant_message)
            db.commit()
            
            return {
                "response": guardrail_violation,
                "is_action": False,
                "ticket_id": None,
                "retrieved_context": [],
                "token_usage": None
            }

        # 2. Gerenciamento de Memória: janela de 5 mensagens + sumarização
        db_messages = conversation.messages
        total_msg_count = len(db_messages)
        
        state_messages = []
        
        # Se houver histórico sumarizado anterior, adicionamos no início
        if conversation.summarized_history:
            state_messages.append({
                "role": "system",
                "content": f"Resumo das interações anteriores da conversa: {conversation.summarized_history}"
            })

        # Se houver mais de 5 mensagens, sumarizamos o excedente anterior
        if total_msg_count > 5:
            # Mensagens para manter na janela ativa (últimas 5)
            active_db_messages = db_messages[-5:]
            # Mensagens que vão para a fila de sumarização (todas anteriores às últimas 5)
            messages_to_summarize = db_messages[:-5]
            
            # Executa sumarização se existirem novas mensagens fora da janela ativa
            try:
                llm = get_text_llm(temperature=0)
                
                formatted_history = []
                for m in messages_to_summarize:
                    formatted_history.append(f"{m.role.upper()}: {m.content}")
                history_text = "\n".join(formatted_history)
                
                summary_prompt = (
                    "Resuma as seguintes mensagens de histórico de chat de suporte de forma concisa.\n"
                    "Destaque principalmente quais eram os problemas relatados e o que já foi tentado:\n\n"
                    f"{history_text}\n\n"
                    "Resumo:"
                )
                
                res = llm.invoke([HumanMessage(content=summary_prompt)])
                new_summary = res.content
                
                # Se já havia um resumo anterior, consolida
                if conversation.summarized_history:
                    consolidation_prompt = (
                        "Consolide estes dois resumos de chat de suporte técnico em um único resumo coeso:\n\n"
                        f"Resumo 1: {conversation.summarized_history}\n\n"
                        f"Resumo 2: {new_summary}\n\n"
                        "Resumo Consolidado:"
                    )
                    res_consolidated = llm.invoke([HumanMessage(content=consolidation_prompt)])
                    conversation.summarized_history = res_consolidated.content
                else:
                    conversation.summarized_history = new_summary
                
                # Atualiza a primeira mensagem do state com o resumo atualizado
                state_messages = [{
                    "role": "system",
                    "content": f"Resumo das interações anteriores da conversa: {conversation.summarized_history}"
                }]
                db.commit()
            except Exception as e:
                logger.error(f"Erro durante a sumarização do histórico: {str(e)}")
                # Em caso de erro, caímos no fallback de usar tudo ou manter o resumo antigo
                active_db_messages = db_messages
            
            # Adiciona as mensagens ativas da janela de 5
            for m in active_db_messages:
                state_messages.append({
                    "role": m.role,
                    "content": m.content
                })
        else:
            # Se forem 5 mensagens ou menos, traz tudo sem sumarização
            for m in db_messages:
                state_messages.append({
                    "role": m.role,
                    "content": m.content
                })

        # 3. Invoca a Execução do Grafo LangGraph
        inputs = {
            "messages": state_messages,
            "current_query": current_query,
            "tenant_id": tenant_id,
            "image_base64": image_base64,
            "image_context": None,
            "retrieved_context": [],
            "response": None,
            "is_action": False,
            "ticket_id": None,
            "token_usage": None
        }
        
        logger.info("Executando a máquina de estados do Agente...")
        try:
            output = self.graph.invoke(inputs)
        except Exception as e:
            logger.error(f"Erro de Contingência (Rede/API): {str(e)}")
            contingency_msg = (
                "Olá! Identificamos uma instabilidade temporária de rede com nossos servidores de nuvem. "
                "Para garantir que sua solicitação não seja perdida, ativamos o protocolo de contingência e "
                "geramos automaticamente o chamado **TK-CONTINGENCIA** para nossa equipe de Nível 2. "
                "Agradecemos a compreensão!"
            )
            output = {
                "response": contingency_msg,
                "is_action": True,
                "ticket_id": "TK-CONTINGENCIA",
                "retrieved_context": [],
                "token_usage": None
            }
        
        # 4. Salva a nova interação no Banco de Dados
        # Salva mensagem do Usuário
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=current_query,
            image_url=image_base64  # salvamos o base64 para histórico do MVP
        )
        db.add(user_message)
        
        # Salva resposta do Assistente
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=output.get("response", "Desculpe, não consegui processar sua dúvida."),
            is_action=output.get("is_action", False),
            ticket_id=output.get("ticket_id")
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        return {
            "response": assistant_message.content,
            "is_action": assistant_message.is_action,
            "ticket_id": assistant_message.ticket_id,
            "retrieved_context": output.get("retrieved_context", []),
            "token_usage": output.get("token_usage")
        }
