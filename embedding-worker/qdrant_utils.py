import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from typing import List, Dict

# Use Qdrant Cloud environment variables
QDRANT_URL = os.getenv("QDRANT_URL") or os.getenv("VECTOR_STORE_URL", "http://vector-store:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "classgpt_chunks")

# Default vector size for OpenAI ada-002 and MiniLM
VECTOR_SIZE = int(os.getenv("EMBEDDING_DIM", "1536"))

print(f"[CLASSGPT_DEBUG] Qdrant URL: {QDRANT_URL}")
print(f"[CLASSGPT_DEBUG] Qdrant API Key: {'SET' if QDRANT_API_KEY else 'NOT SET'}")
print(f"[CLASSGPT_DEBUG] Collection name: {COLLECTION_NAME}")
print(f"[CLASSGPT_DEBUG] Vector size: {VECTOR_SIZE}")

# Create client with API key if available
if QDRANT_API_KEY:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    print(f"[CLASSGPT_DEBUG] Created Qdrant client with API key")
else:
    client = QdrantClient(url=QDRANT_URL)
    print(f"[CLASSGPT_DEBUG] Created Qdrant client without API key")

def ensure_collection():
    try:
        print(f"[CLASSGPT_DEBUG] Ensuring collection '{COLLECTION_NAME}' exists...")
        # Try to create the collection, ignore if it already exists
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )
        print(f"[CLASSGPT_DEBUG] Created collection '{COLLECTION_NAME}'")
    except Exception as e:
        # Collection already exists, which is fine
        print(f"[CLASSGPT_DEBUG] Collection '{COLLECTION_NAME}' already exists or error: {e}")

def upsert_embeddings(document_id: str, chunks: List[str], embeddings: List[List[float]], metadata: List[Dict]):
    print(f"[CLASSGPT_DEBUG] Upserting {len(chunks)} embeddings for document {document_id}")
    ensure_collection()
    
    points = []
    for i, (chunk, embedding, meta) in enumerate(zip(chunks, embeddings, metadata)):
        point = PointStruct(
            id=str(uuid.uuid4()),  # Unique UUID for each chunk
            vector=embedding,
            payload={
                "document_id": document_id,
                "chunk_index": i,
                "content": chunk,
                **meta
            }
        )
        points.append(point)
    
    try:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"[CLASSGPT_DEBUG] Successfully upserted {len(points)} points to Qdrant")
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Error upserting to Qdrant: {e}")
        raise 