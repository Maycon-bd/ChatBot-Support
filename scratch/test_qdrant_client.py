import os
from qdrant_client import QdrantClient

path = "./qdrant_data"
print("Initializing client with path:", path)
try:
    client = QdrantClient(path=path)
    print("Type of client:", type(client))
    print("Has search attribute:", hasattr(client, "search"))
    print("Dir:", [d for d in dir(client) if not d.startswith("_")])
except Exception as e:
    print("Error:", e)
