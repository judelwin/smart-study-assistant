import os
from pinecone import Pinecone
from typing import List, Dict

# Pinecone environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "classgpt-chunks")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

def search_embeddings(query_vector: List[float], top_k: int = 5, filter_metadata: Dict = None):
    """Search embeddings in Pinecone index"""
    if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
        raise ValueError("Pinecone credentials not configured")
    
    # Get the index
    index = pc.Index(INDEX_NAME)
    
    # Prepare query parameters
    query_params = {
        "vector": query_vector,
        "top_k": top_k,
        "include_metadata": True
    }
    
    # Add filter if provided
    if filter_metadata:
        query_params["filter"] = filter_metadata
    
    try:
        # Perform the query
        results = index.query(**query_params)
        
        # Convert Pinecone results to match Qdrant format
        hits = []
        for match in results.matches:
            hit = {
                "id": match.id,
                "score": match.score,
                "payload": match.metadata
            }
            hits.append(hit)
        
        return hits
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Error searching Pinecone: {e}")
        raise 