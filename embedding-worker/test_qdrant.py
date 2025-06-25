import os
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

QDRANT_URL = os.getenv("QDRANT_URL") or os.getenv("VECTOR_STORE_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

print(f"QDRANT_URL: {QDRANT_URL}")
print(f"QDRANT_API_KEY: {'SET' if QDRANT_API_KEY else 'NOT SET'}")

try:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    print("✅ Connected to Qdrant!")
    collections = client.get_collections()
    print(f"Collections: {collections}")
except UnexpectedResponse as e:
    print(f"❌ Qdrant responded with error: {e}")
except Exception as e:
    print(f"❌ Failed to connect to Qdrant: {e}") 