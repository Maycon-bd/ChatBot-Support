import qdrant_client
print("qdrant_client file:", qdrant_client.__file__)
import inspect
print("QdrantClient source file:", inspect.getfile(qdrant_client.QdrantClient))
