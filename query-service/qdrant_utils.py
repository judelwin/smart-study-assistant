import os
from qdrant_client import QdrantClient
from typing import List, Dict

# Use Qdrant Cloud environment variables
QDRANT_URL = os.getenv("QDRANT_URL") or os.getenv("VECTOR_STORE_URL", "http://vector-store:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "classgpt_chunks")

# Create client with API key if available
if QDRANT_API_KEY:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
else:
    client = QdrantClient(url=QDRANT_URL)

def search_embeddings(query_vector: List[float], top_k: int = 5, filter_payload: Dict = None):
    search_params = {}
    if filter_payload:
        search_params['query_filter'] = filter_payload
    hits = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        **search_params
    )
    return hits 