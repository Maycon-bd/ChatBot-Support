import logging
from fastapi import APIRouter, Depends, Header, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.database import get_db
from app.services.qdrant_service import QdrantService, get_qdrant_client
from app.services import qdrant_service as qs_module
from app.models.tenant import Tenant
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


# ─────────────────────────────────────────────
# Helper: valida chave de admin
# ─────────────────────────────────────────────
def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de administrador inválida."
        )


# ─────────────────────────────────────────────
# POST /upload  (apenas admin)
# ─────────────────────────────────────────────
@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    x_tenant_id: str = Header("quantum_corp", alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """
    [ADMIN] Recebe um documento (.txt / .md / .html) e executa
    ingestão + indexação vetorial no Qdrant para o tenant ativo.
    Requer cabeçalho X-Admin-Key com a senha correta.
    """
    # Garante que o Tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == x_tenant_id).first()
    if not tenant:
        tenant = Tenant(id=x_tenant_id, name=f"Tenant ({x_tenant_id})")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    filename = file.filename
    if not filename.endswith((".txt", ".md", ".html")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos .txt, .md ou .html são suportados."
        )

    try:
        content_bytes = file.file.read()
        document_text = content_bytes.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao ler o arquivo: {str(e)}"
        )

    if not document_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio."
        )

    try:
        qdrant_svc = QdrantService()
        point_ids = qdrant_svc.ingest_document(
            text=document_text,
            tenant_id=x_tenant_id,
            source_name=filename
        )
        return {
            "message": f"'{filename}' indexado com sucesso.",
            "tenant_id": x_tenant_id,
            "chunks_count": len(point_ids),
        }
    except Exception as e:
        logger.error(f"Erro na ingestão de {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no Qdrant: {str(e)}"
        )


# ─────────────────────────────────────────────
# GET /list  (apenas admin) — lista fontes únicas
# ─────────────────────────────────────────────
@router.get("/list")
def list_documents(
    x_tenant_id: str = Header("quantum_corp", alias="X-Tenant-ID"),
    _: None = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """
    [ADMIN] Retorna a lista de fontes (arquivos) indexados no Qdrant
    para o tenant ativo, com a contagem de chunks por fonte.
    """
    try:
        client = get_qdrant_client()
        # Scroll de todos os pontos do tenant
        scroll_results, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=x_tenant_id))
                ]
            ),
            limit=5000,
            with_payload=True,
            with_vectors=False
        )

        # Agrupa por source
        sources: Dict[str, int] = {}
        for pt in scroll_results:
            if pt.payload:
                src = pt.payload.get("source", "desconhecido")
                sources[src] = sources.get(src, 0) + 1

        return [
            {"source": src, "chunks": count}
            for src, count in sorted(sources.items())
        ]
    except Exception as e:
        logger.error("Erro ao listar documentos", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar Qdrant: {str(e)}"
        )


# ─────────────────────────────────────────────
# DELETE /delete/{source}  (apenas admin)
# ─────────────────────────────────────────────
@router.delete("/delete")
def delete_document(
    source: str,
    x_tenant_id: str = Header("quantum_corp", alias="X-Tenant-ID"),
    _: None = Depends(require_admin)
):
    """
    [ADMIN] Remove todos os chunks de uma fonte (arquivo) específica
    do índice vetorial do tenant ativo no Qdrant.
    """
    try:
        client = get_qdrant_client()
        client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=x_tenant_id)),
                    FieldCondition(key="source",    match=MatchValue(value=source)),
                ]
            )
        )
        logger.info(f"Documento '{source}' removido do tenant '{x_tenant_id}'.")
        return {"message": f"Documento '{source}' removido com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao remover documento '{source}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover do Qdrant: {str(e)}"
        )
