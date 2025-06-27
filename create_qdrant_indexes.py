import os
from qdrant_client import QdrantClient

QDRANT_URL = os.environ["QDRANT_URL"]
QDRANT_API_KEY = os.environ["QDRANT_API_KEY"]
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "classgpt_chunks")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

print(f"Creating payload index for 'user_id'...")
client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="user_id",
    field_schema="keyword"
)
print("Done.")

print(f"Creating payload index for 'class_id'...")
client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="class_id",
    field_schema="keyword"
)
print("Done.") 