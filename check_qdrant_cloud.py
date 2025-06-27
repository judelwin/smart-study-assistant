import os
from qdrant_client import QdrantClient

# Use the same environment variables as the services
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "classgpt_chunks")

print(f"Qdrant URL: {QDRANT_URL}")
print(f"Qdrant API Key: {'SET' if QDRANT_API_KEY else 'NOT SET'}")
print(f"Collection name: {COLLECTION_NAME}")

if not QDRANT_URL:
    print("ERROR: QDRANT_URL environment variable not set!")
    exit(1)

# Create client
if QDRANT_API_KEY:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
else:
    client = QdrantClient(url=QDRANT_URL)

try:
    # Get collection info
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"\nCollection info: {collection_info}")
    
    # Get some points
    points, _ = client.scroll(collection_name=COLLECTION_NAME, limit=10)
    print(f"\nFound {len(points)} points in collection")
    
    for i, point in enumerate(points):
        print(f"\nPoint {i+1}:")
        print(f"  ID: {point.id}")
        print(f"  Payload keys: {list(point.payload.keys())}")
        if 'content' in point.payload:
            content = point.payload['content']
            print(f"  Content preview: {content[:200]}...")
        if 'user_id' in point.payload:
            print(f"  User ID: {point.payload['user_id']}")
        if 'class_id' in point.payload:
            print(f"  Class ID: {point.payload['class_id']}")
        if 'document_id' in point.payload:
            print(f"  Document ID: {point.payload['document_id']}")
            
except Exception as e:
    print(f"Error accessing Qdrant: {e}") 