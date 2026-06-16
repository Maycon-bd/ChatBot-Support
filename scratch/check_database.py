import sys
from pathlib import Path

# Ajusta PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.services.qdrant_service import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue

def check_database():
    print("="*60)
    print("🔍 DIAGNÓSTICO DO BANCO DE DADOS VETORIAL (QDRANT)")
    print("="*60)
    
    try:
        client = get_qdrant_client()
        
        # 1. Recupera as informações da coleção
        collection_info = client.get_collection(collection_name=settings.QDRANT_COLLECTION_NAME)
        print(f"Coleção ativa: {settings.QDRANT_COLLECTION_NAME}")
        print(f"Status: {collection_info.status}")
        print(f"Total de vetores/pontos (Geral): {collection_info.points_count}")
        print("-"*60)
        
        # 2. Faz scroll de todos os pontos para agrupar por Tenant e por Arquivo Fonte
        # Limite de 10.000 pontos para scroll de metadados
        scroll_results, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
        
        if not scroll_results:
            print("Nenhum documento indexado no Qdrant.")
            return

        # Agrupamento de dados
        tenants = {}
        for pt in scroll_results:
            if not pt.payload:
                continue
            tenant = pt.payload.get("tenant_id", "desconhecido")
            source = pt.payload.get("source", "desconhecido")
            
            if tenant not in tenants:
                tenants[tenant] = {}
            
            tenants[tenant][source] = tenants[tenant].get(source, 0) + 1

        print("Distribuição de Documentos por Tenant:")
        for tenant, sources in tenants.items():
            print(f"\n👤 Tenant ID: '{tenant}'")
            print(f"   Total de arquivos diferentes: {len(sources)}")
            print(f"   Detalhes dos arquivos:")
            for src, chunks in sorted(sources.items()):
                print(f"    - {src} ({chunks} chunks/vetores)")
                
    except Exception as e:
        print(f"Erro ao conectar ou ler dados do Qdrant: {str(e)}")
        print("Certifique-se de que o servidor FastAPI ou outros scripts não estejam segurando o lock do Qdrant.")
        
    print("="*60)

if __name__ == "__main__":
    check_database()
