from qdrant_client import QdrantClient

try:
    client = QdrantClient(":memory:")
    print("Instance type:", type(client))
    print("Instance has search attribute:", hasattr(client, "search"))
    methods = [m for m in dir(client) if not m.startswith("_")]
    print("Instance methods:", "search" in methods)
    print("All instance methods:", methods)
except Exception as e:
    print("Error:", e)
