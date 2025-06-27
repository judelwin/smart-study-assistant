from qdrant_client import QdrantClient, models

client = QdrantClient("http://localhost:6333")

client.recreate_collection(
    collection_name="classgpt_chunks",
    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
    payload_schema={
        "user_id": models.PayloadSchemaType.KEYWORD,
        "class_id": models.PayloadSchemaType.KEYWORD,
    }
)

print("Collection created with payload indexes for user_id and class_id.") 