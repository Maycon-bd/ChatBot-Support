import sys
from qdrant_client import QdrantClient

print("Python path:", sys.path)
print("QdrantClient type:", type(QdrantClient))
print("QdrantClient module:", QdrantClient.__module__)
print("Has search attribute in class:", hasattr(QdrantClient, "search"))

# Inspect methods
methods = [m for m in dir(QdrantClient) if not m.startswith("_")]
print("Available methods:", methods)
