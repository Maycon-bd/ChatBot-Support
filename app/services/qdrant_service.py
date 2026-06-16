import uuid
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from app.config import settings

logger = logging.getLogger(__name__)

# Instância global do QdrantClient compartilhada por todas as instâncias do serviço
_qdrant_client = None

def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        if settings.QDRANT_URL:
            logger.info(f"Conectando ao Qdrant via URL: {settings.QDRANT_URL}")
            _qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        elif settings.QDRANT_PATH:
            logger.info(f"Conectando ao Qdrant via Caminho Local: {settings.QDRANT_PATH}")
            _qdrant_client = QdrantClient(path=settings.QDRANT_PATH)
        else:
            logger.info("Conectando ao Qdrant em Modo Memória (:memory:)")
            _qdrant_client = QdrantClient(":memory:")
    return _qdrant_client

class QdrantService:
    def __init__(self):
        # 1. Obtém o cliente Qdrant global compartilhado
        self.client = get_qdrant_client()

        # 2. Inicializa o modelo de Embeddings Local (all-MiniLM-L6-v2: 384 dimensões)
        try:
            logger.info("Inicializando modelo de embeddings local: sentence-transformers/all-MiniLM-L6-v2")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            # O Semantic Chunker divide o texto semanticamente de forma inteligente
            self.text_splitter = SemanticChunker(self.embeddings)
        except Exception as e:
            logger.error(f"Erro ao inicializar o modelo de embeddings local: {str(e)}")
            self.embeddings = None
            self.text_splitter = None

        # 3. Garante que a coleção existe no Qdrant com dimensões corretas
        self.ensure_collection()

    def ensure_collection(self):
        """Garante a existência da coleção para armazenar os manuais de suporte."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            target_size = 384  # Dimensão do sentence-transformers/all-MiniLM-L6-v2
            
            if settings.QDRANT_COLLECTION_NAME in collection_names:
                info = self.client.get_collection(collection_name=settings.QDRANT_COLLECTION_NAME)
                # No Qdrant, o size do vetor fica em config.params.vectors.size
                current_size = info.config.params.vectors.size
                if current_size != target_size:
                    logger.warning(f"Dimensão da coleção existente ({current_size}) não coincide com a nova ({target_size}). Recriando coleção...")
                    self.client.delete_collection(collection_name=settings.QDRANT_COLLECTION_NAME)
                    collection_names.remove(settings.QDRANT_COLLECTION_NAME)
            
            if settings.QDRANT_COLLECTION_NAME not in collection_names:
                logger.info(f"Criando coleção '{settings.QDRANT_COLLECTION_NAME}' no Qdrant com dimensão {target_size}...")
                self.client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=target_size,
                        distance=Distance.COSINE
                    )
                )
            else:
                logger.info(f"Coleção '{settings.QDRANT_COLLECTION_NAME}' já existe com a dimensão correta.")
        except Exception as e:
            logger.error(f"Erro ao verificar/criar coleção no Qdrant: {str(e)}")

    def ingest_document(self, text: str, tenant_id: str, source_name: str) -> List[str]:
        """
        Divide o documento em chunks semânticos, gera os embeddings e
        insere no Qdrant vinculando o tenant_id como metadado (payload).
        """
        if not self.embeddings:
            raise ValueError("O modelo de embeddings não está configurado.")

        if not text.strip():
            return []

        # 1. Executa o Semantic Chunking do LangChain
        logger.info(f"Iniciando Semantic Chunking para {source_name} - Tenant: {tenant_id}")
        chunks = self.text_splitter.split_text(text)
        chunks = [c.strip() for c in chunks if c.strip()]
        logger.info(f"Documento dividido em {len(chunks)} chunks semânticos válidos.")

        if not chunks:
            return []

        # 2. Gera os embeddings para todos os chunks
        embeddings_list = self.embeddings.embed_documents(chunks)

        # 3. Prepara os pontos para inserção no Qdrant
        points = []
        point_ids = []
        for idx, (chunk_text, vector) in enumerate(zip(chunks, embeddings_list)):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "tenant_id": tenant_id,
                        "page_content": chunk_text,
                        "source": source_name,
                        "chunk_index": idx
                    }
                )
            )

        # 4. Faz o upload para o Qdrant
        self.client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=points
        )
        logger.info(f"Ingestão concluída com sucesso. {len(points)} pontos salvos.")
        return point_ids

    def hybrid_search(self, query: str, tenant_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Realiza a busca híbrida (Semântica + BM25) com isolamento estrito de tenant_id,
        aplicando Reciprocal Rank Fusion (RRF) como etapa de reclassificação (Reranker).
        """
        if not self.embeddings:
            raise ValueError("O modelo de embeddings não está configurado.")

        # 1. Filtro estrito de Tenant no Payload do Qdrant
        tenant_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )
            ]
        )

        # 2. Busca Semântica (Dense Vector) — usando a Query API unificada (qdrant-client ≥ 1.10)
        query_vector = self.embeddings.embed_query(query)
        dense_response = self.client.query_points(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query=query_vector,
            query_filter=tenant_filter,
            limit=top_k * 2,  # Busca um pouco mais para a fusão
            with_payload=True
        )
        dense_results = dense_response.points

        # 3. Busca por Palavra-Chave (BM25)
        # Recupera os documentos apenas do tenant ativo para indexação local temporária
        # Isso garante que um tenant nunca veja palavras-chave de outro tenant
        scroll_results = self.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            scroll_filter=tenant_filter,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )[0]

        bm25_results = []
        if scroll_results:
            # Converte os pontos scrollados em objetos Document do LangChain
            documents = [
                Document(
                    page_content=pt.payload["page_content"],
                    metadata={
                        "id": pt.id,
                        "source": pt.payload.get("source", "unknown"),
                        "chunk_index": pt.payload.get("chunk_index", 0)
                    }
                )
                for pt in scroll_results if pt.payload and "page_content" in pt.payload
            ]
            
            try:
                # Inicializa o recuperador BM25 em memória com os documentos desse tenant
                bm25_retriever = BM25Retriever.from_documents(documents)
                bm25_retriever.k = top_k * 2
                bm25_docs = bm25_retriever.invoke(query)
                bm25_results = bm25_docs
            except Exception as e:
                logger.error(f"Erro ao instanciar ou executar busca BM25: {str(e)}")

        # 4. Reranking por Reciprocal Rank Fusion (RRF)
        # Combina os rankings das duas buscas usando a fórmula RRF
        rrf_scores = {}
        k = 60  # Constante padrão do RRF
        
        # Mapeamento para guardar o conteúdo dos chunks
        doc_details = {}

        # Processa os resultados Dense
        for rank, hit in enumerate(dense_results):
            doc_id = hit.id
            doc_details[doc_id] = {
                "page_content": hit.payload.get("page_content", ""),
                "source": hit.payload.get("source", ""),
                "chunk_index": hit.payload.get("chunk_index", 0),
                "score_dense": hit.score
            }
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + (rank + 1)))

        # Processa os resultados BM25
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.metadata.get("id")
            if not doc_id:
                continue
            if doc_id not in doc_details:
                doc_details[doc_id] = {
                    "page_content": doc.page_content,
                    "source": doc.metadata.get("source", ""),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "score_dense": 0.0
                }
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + (rank + 1)))

        # Ordena pelo Score do RRF (Maior é melhor)
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Retorna os top_k classificados
        final_results = []
        for doc_id, rrf_score in sorted_docs[:top_k]:
            details = doc_details[doc_id]
            final_results.append({
                "id": doc_id,
                "page_content": details["page_content"],
                "source": details["source"],
                "chunk_index": details["chunk_index"],
                "rrf_score": rrf_score,
                "score_dense": details["score_dense"]
            })

        logger.info(f"Busca híbrida retornou {len(final_results)} resultados ordenados via RRF.")
        return final_results
