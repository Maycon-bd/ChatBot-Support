from qdrant_client import QdrantClient

client = QdrantClient(":memory:")
print("Created client:", client)
try:
    # Try calling search
    client.search(collection_name="test", query_vector=[0.1]*10, limit=1)
except Exception as e:
    import traceback
    traceback.print_exc()
