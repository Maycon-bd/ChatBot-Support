import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Define chaves fictícias no ambiente antes de importar o app
os.environ["GEMINI_API_KEY"] = "mock-gemini-api-key-for-testing"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

class TestMultiTenantArchitecture(unittest.TestCase):
    def setUp(self):
        # 1. Configura um banco de dados relacional em memória para cada teste
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # 2. Cria Tenants e Usuários de teste
        self.tenant_a = Tenant(id="tenant_a", name="Empresa A")
        self.tenant_b = Tenant(id="tenant_b", name="Empresa B")
        self.db.add(self.tenant_a)
        self.db.add(self.tenant_b)
        self.db.commit()

        self.user_a = User(id="user_a", tenant_id="tenant_a", name="User A", email="a@company.com")
        self.user_b = User(id="user_b", tenant_id="tenant_b", name="User B", email="b@company.com")
        self.db.add(self.user_a)
        self.db.add(self.user_b)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_database_isolation(self):
        """Valida que consultas no banco relacional retornam apenas dados do respectivo Tenant."""
        # Cria uma conversa para o Tenant A e uma para o Tenant B
        conv_a = Conversation(id="conv_a", tenant_id="tenant_a", user_id="user_a", title="Chat A")
        conv_b = Conversation(id="conv_b", tenant_id="tenant_b", user_id="user_b", title="Chat B")
        self.db.add(conv_a)
        self.db.add(conv_b)
        self.db.commit()

        # Testa filtro por tenant_id
        conversas_tenant_a = self.db.query(Conversation).filter(Conversation.tenant_id == "tenant_a").all()
        conversas_tenant_b = self.db.query(Conversation).filter(Conversation.tenant_id == "tenant_b").all()

        self.assertEqual(len(conversas_tenant_a), 1)
        self.assertEqual(conversas_tenant_a[0].id, "conv_a")

        self.assertEqual(len(conversas_tenant_b), 1)
        self.assertEqual(conversas_tenant_b[0].id, "conv_b")

    @patch("app.services.qdrant_service.GoogleGenerativeAIEmbeddings")
    @patch("app.services.qdrant_service.SemanticChunker")
    @patch("app.services.qdrant_service.QdrantClient")
    def test_qdrant_tenant_isolation(self, mock_qdrant_client, mock_chunker, mock_embeddings):
        """Valida que a busca no Qdrant aplica filtro obrigatório de tenant_id no payload."""
        from app.services.qdrant_service import QdrantService
        
        # Mocks para o Qdrant
        mock_client_instance = mock_qdrant_client.return_value
        mock_client_instance.get_collections.return_value.collections = []
        
        # Configura o mock do Embeddings
        mock_embeddings_instance = mock_embeddings.return_value
        mock_embeddings_instance.embed_query.return_value = [0.1] * 3072
 
        # Retornos simulados da busca no Qdrant
        mock_hit_tenant_a = MagicMock()
        mock_hit_tenant_a.id = "doc1"
        mock_hit_tenant_a.score = 0.9
        mock_hit_tenant_a.payload = {
            "tenant_id": "tenant_a",
            "page_content": "Manual do Tenant A sobre Wi-Fi",
            "source": "manual_wifi.txt",
            "chunk_index": 0
        }
        # query_points retorna um objeto com .points; simulamos isso
        mock_query_response = MagicMock()
        mock_query_response.points = [mock_hit_tenant_a]
        mock_client_instance.query_points.return_value = mock_query_response
        mock_client_instance.scroll.return_value = ([], None)

        # Inicializa o serviço e realiza busca híbrida
        qdrant_service = QdrantService()
        
        # Busca simulada para o Tenant A
        results = qdrant_service.hybrid_search(query="Como conectar Wi-Fi?", tenant_id="tenant_a", top_k=2)

        # Verifica se o método query_points do QdrantClient foi chamado com o filtro correto
        called_args, called_kwargs = mock_client_instance.query_points.call_args
        
        # Verifica se a query_filter do Qdrant foi passada
        self.assertIn("query_filter", called_kwargs)
        query_filter = called_kwargs["query_filter"]
        
        # Valida que o filtro possui a chave "tenant_id" e valor "tenant_a"
        self.assertEqual(query_filter.must[0].key, "tenant_id")
        self.assertEqual(query_filter.must[0].match.value, "tenant_a")

        # Verifica se o resultado pertence ao Tenant A
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["page_content"], "Manual do Tenant A sobre Wi-Fi")

    @patch("app.services.agent_service.ChatGoogleGenerativeAI")
    @patch("app.services.agent_service.QdrantService")
    def test_langgraph_routing_rag(self, mock_qdrant_service_class, mock_chat_openai_class):
        """Valida que o roteador direciona para o nó RAG e este busca informações na base."""
        from app.services.agent_service import AgentService
        
        # Mock do ChatOpenAI para classificação e resposta
        mock_llm = mock_chat_openai_class.return_value
        
        # Primeira chamada (Router) responde "SUPPORT"
        # Segunda chamada (RAG) responde com a resposta de suporte técnico
        mock_router_response = MagicMock()
        mock_router_response.content = "SUPPORT"
        
        mock_rag_response = MagicMock()
        mock_rag_response.content = "Para configurar o Wi-Fi, conecte na rede Admin-A."
        
        mock_llm.invoke.side_effect = [mock_router_response, mock_rag_response]

        # Mock do QdrantService
        mock_qdrant_service = mock_qdrant_service_class.return_value
        mock_qdrant_service.hybrid_search.return_value = [{
            "id": "1",
            "page_content": "Use a rede Admin-A.",
            "source": "manual.txt",
            "chunk_index": 0,
            "rrf_score": 1.0,
            "score_dense": 0.9
        }]

        # Cria conversa no banco
        conv = Conversation(id="conv_1", tenant_id="tenant_a", user_id="user_a", title="Chat Test")
        self.db.add(conv)
        self.db.commit()

        agent_service = AgentService()
        result = agent_service.run_agent(
            db=self.db,
            conversation_id="conv_1",
            tenant_id="tenant_a",
            current_query="Como configuro o Wi-Fi?"
        )

        # Valida que o RAG Node foi executado e retornou resposta
        self.assertEqual(result["response"], "Para configurar o Wi-Fi, conecte na rede Admin-A.")
        self.assertFalse(result["is_action"])
        self.assertIn("Use a rede Admin-A.", result["retrieved_context"])

    @patch("app.services.agent_service.ChatGoogleGenerativeAI")
    def test_langgraph_routing_action(self, mock_chat_openai_class):
        """Valida que solicitações de abertura de chamado vão para o nó de Ação e abrem ticket."""
        from app.services.agent_service import AgentService
        
        # Mock do ChatOpenAI que classifica a intenção como "TICKET"
        mock_llm = mock_chat_openai_class.return_value
        mock_router_response = MagicMock()
        mock_router_response.content = "TICKET"
        mock_llm.invoke.return_value = mock_router_response

        # Cria conversa no banco
        conv = Conversation(id="conv_2", tenant_id="tenant_a", user_id="user_a", title="Chat Ticket")
        self.db.add(conv)
        self.db.commit()

        agent_service = AgentService()
        result = agent_service.run_agent(
            db=self.db,
            conversation_id="conv_2",
            tenant_id="tenant_a",
            current_query="Por favor, abra um chamado técnico para mim."
        )

        # Valida que a resposta foi gerada pelo Action Node e gerou um ticket
        self.assertTrue(result["is_action"])
        self.assertIsNotNone(result["ticket_id"])
        self.assertTrue(result["ticket_id"].startswith("TK-"))
        self.assertIn("chamado", result["response"])

if __name__ == "__main__":
    unittest.main()
