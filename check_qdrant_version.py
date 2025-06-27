import requests
import json

# Check Qdrant version
try:
    response = requests.get("http://localhost:6333/version")
    if response.status_code == 200:
        version_info = response.json()
        print(f"Qdrant version: {version_info}")
    else:
        print(f"Failed to get version: {response.status_code}")
except Exception as e:
    print(f"Error checking version: {e}")

# Test if we can create a collection with payload_schema
from qdrant_client import QdrantClient
from qdrant_client.http import models

try:
    client = QdrantClient("localhost", port=6333)
    
    # Try to create collection with payload_schema
    print("\nAttempting to create collection with payload_schema...")
    client.recreate_collection(
        collection_name="test_collection",
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        payload_schema={
            "user_id": models.PayloadSchemaTypeKeyword(),
            "class_id": models.PayloadSchemaTypeKeyword(),
        }
    )
    print("✅ Successfully created collection with payload_schema!")
    
    # Add a dummy point
    client.upsert(
        collection_name="test_collection",
        points=[
            models.PointStruct(
                id=1,
                vector=[0.0]*1536,
                payload={"user_id": "dummy", "class_id": "dummy"}
            )
        ]
    )
    print("✅ Successfully added dummy point!")
    
    # Clean up
    client.delete_collection("test_collection")
    print("✅ Cleaned up test collection")
    
except Exception as e:
    print(f"❌ Error with payload_schema: {e}")
    print(f"Error type: {type(e)}") 