from qdrant_client import QdrantClient, models
import numpy as np

client = QdrantClient("http://localhost:6333")

client.upsert(
    collection_name="classgpt_chunks",
    points=[
        models.PointStruct(
            id=1,
            vector=np.random.rand(1536).tolist(),
            payload={"user_id": "dummy", "class_id": "dummy"}
        )
    ]
)
print("Dummy point added.") 