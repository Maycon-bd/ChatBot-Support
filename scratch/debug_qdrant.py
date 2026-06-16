import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import logging
logging.basicConfig(level=logging.DEBUG)

from app.services.qdrant_service import get_qdrant_client
from app.config import settings
from qdrant_client.models import Filter, FieldCondition, MatchValue

def debug():
    client = get_qdrant_client()
    print("Cliente inicializado:", client)
    try:
        scroll_results, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value="quantum_corp"))
                ]
            ),
            limit=5000,
            with_payload=True,
            with_vectors=False
        )
        print(f"Sucesso: {len(scroll_results)} pontos encontrados.")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug()
