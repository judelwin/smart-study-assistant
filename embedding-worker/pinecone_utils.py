import os
import uuid
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict

# Pinecone environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")  # e.g., "us-east-1"
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "classgpt-chunks")

# Default vector size for OpenAI ada-002 and MiniLM
VECTOR_SIZE = int(os.getenv("EMBEDDING_DIM", "1536"))

print(f"[CLASSGPT_DEBUG] Pinecone Environment: {PINECONE_ENVIRONMENT}")
print(f"[CLASSGPT_DEBUG] Pinecone API Key: {'SET' if PINECONE_API_KEY else 'NOT SET'}")
print(f"[CLASSGPT_DEBUG] Index name: {INDEX_NAME}")
print(f"[CLASSGPT_DEBUG] Vector size: {VECTOR_SIZE}")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

def ensure_index():
    """Create Pinecone index if it doesn't exist"""
    try:
        print(f"[CLASSGPT_DEBUG] Ensuring index '{INDEX_NAME}' exists...")
        
        # Check if index exists
        if INDEX_NAME not in pc.list_indexes().names():
            print(f"[CLASSGPT_DEBUG] Creating index '{INDEX_NAME}'...")
            pc.create_index(
                name=INDEX_NAME,
                dimension=VECTOR_SIZE,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT)
            )
            print(f"[CLASSGPT_DEBUG] Created index '{INDEX_NAME}' with metadata indexing")
        else:
            print(f"[CLASSGPT_DEBUG] Index '{INDEX_NAME}' already exists")
            
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Error ensuring index: {e}")
        raise

def upsert_embeddings(document_id: str, chunks: List[str], embeddings: List[List[float]], metadata: List[Dict]):
    """Upsert embeddings to Pinecone index"""
    print(f"[CLASSGPT_DEBUG] Upserting {len(chunks)} embeddings for document {document_id}")
    
    if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
        raise ValueError("Pinecone credentials not configured")
    
    ensure_index()
    
    # Get the index
    index = pc.Index(INDEX_NAME)
    
    # Prepare vectors for upsert
    vectors = []
    for i, (chunk, embedding, meta) in enumerate(zip(chunks, embeddings, metadata)):
        vector_id = str(uuid.uuid4())  # Unique ID for each chunk
        
        # Prepare metadata for Pinecone
        vector_metadata = {
            "document_id": document_id,
            "chunk_index": i,
            "content": chunk,
            **meta  # This includes user_id, class_id, etc.
        }
        
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": vector_metadata
        })
    
    try:
        # Upsert in batches (Pinecone recommends batches of 100)
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
        
        print(f"[CLASSGPT_DEBUG] Successfully upserted {len(vectors)} vectors to Pinecone")
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Error upserting to Pinecone: {e}")
        raise

def delete_document_vectors(document_id: str):
    """Delete all vectors for a specific document"""
    try:
        index = pc.Index(INDEX_NAME)
        index.delete(filter={"document_id": document_id})
        print(f"[CLASSGPT_DEBUG] Successfully deleted vectors for document {document_id}")
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Error deleting vectors for document {document_id}: {e}")
        raise 