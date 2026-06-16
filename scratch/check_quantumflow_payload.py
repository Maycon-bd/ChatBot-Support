import sys
from pathlib import Path

# Ajusta PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

def check_payload():
    client = QdrantClient(path=str(ROOT_DIR / "qdrant_data"))
    
    # Busca pontos onde a fonte é manual_oficial_quantumflow.txt
    results, _ = client.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="source", match=MatchValue(value="manual_oficial_quantumflow.txt"))
            ]
        ),
        limit=10,
        with_payload=True,
        with_vectors=False
    )
    
    print(f"Total de pontos encontrados: {len(results)}")
    for i, pt in enumerate(results):
        print(f"\n--- PONTO {i+1} ---")
        print(f"Metadata: {pt.payload.get('tenant_id')}, {pt.payload.get('source')}")
        print("Conteúdo:")
        print(pt.payload.get("page_content"))

if __name__ == "__main__":
    check_payload()
