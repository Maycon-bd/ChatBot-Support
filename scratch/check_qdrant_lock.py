import sys
from qdrant_client import QdrantClient

try:
    print("Tentando conectar ao Qdrant local em ./qdrant_data...")
    client = QdrantClient(path="./qdrant_data")
    collections = client.get_collections()
    print("Conexão bem sucedida!")
    print("Coleções:", collections)
except Exception as e:
    print("ERRO ao conectar:", str(e), file=sys.stderr)
