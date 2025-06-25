import os
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL") or os.getenv("VECTOR_STORE_URL", "http://vector-store:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "classgpt_chunks")

if QDRANT_API_KEY:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
else:
    client = QdrantClient(url=QDRANT_URL)

print(f"Clearing Qdrant collection '{COLLECTION_NAME}' at {QDRANT_URL} ...")
client.delete_collection(collection_name=COLLECTION_NAME)
print("Collection deleted. It will be recreated when new embeddings are added.") 