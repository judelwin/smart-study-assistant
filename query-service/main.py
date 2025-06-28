from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from embedding_providers import get_embedding_provider
from pinecone_utils import search_embeddings
from typing import List, Optional
from openai import OpenAI
import os
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests
from fastapi import Depends
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI(
    title="ClassGPT Query Service",
    description="RAG pipeline and search endpoint for ClassGPT.",
    version="1.0.0",
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Conservative limits for personal project ($5-10/month budget)
MAX_QUERY_LENGTH = 500  # Max 500 characters per query
MAX_QUERIES_PER_HOUR = 30  # Max 30 queries per hour per user
MAX_TOP_K = 10  # Max 10 results per query

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    class_id: Optional[str] = None
    document_id: Optional[str] = None

class ChunkResult(BaseModel):
    content: str
    document_id: str
    chunk_index: int
    score: float
    page_number: int = -1
    payload: dict

class LLMResponse(BaseModel):
    answer: str
    chunks: List[ChunkResult]

security = HTTPBearer()
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8002/me")

# Helper to get user_id from JWT
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    headers = {"Authorization": f"Bearer {credentials.credentials}"}
    try:
        resp = requests.get(AUTH_SERVICE_URL, headers=headers, timeout=5)
        resp.raise_for_status()
        return resp.json()["id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/query", response_model=LLMResponse)
@limiter.limit("30/hour")  # Rate limit: 30 queries per hour per IP
def query_chunks(request: QueryRequest, user_id: str = Depends(get_current_user_id)):
    # Validate query length
    if len(request.query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail=f"Query too long. Maximum {MAX_QUERY_LENGTH} characters allowed."
        )
    
    # Validate top_k
    if request.top_k and request.top_k > MAX_TOP_K:
        raise HTTPException(
            status_code=400, 
            detail=f"top_k too high. Maximum {MAX_TOP_K} results allowed."
        )
    
    embedding_provider = get_embedding_provider()
    query_embedding = embedding_provider.embed([request.query])[0]
    
    # Filter by user_id and class_id or document_id
    filter_metadata = {"user_id": user_id}
    if request.class_id:
        filter_metadata["class_id"] = request.class_id
    elif request.document_id:
        filter_metadata["document_id"] = request.document_id
    
    print(f"[DEBUG] Query embedding shape: {len(query_embedding)}")
    print(f"[DEBUG] Pinecone filter: {filter_metadata}")
    print(f"[DEBUG] Query: {request.query}")

    hits = search_embeddings(query_embedding, top_k=request.top_k, filter_metadata=filter_metadata)
    print(f"[DEBUG] Pinecone hits returned: {len(hits)}")
    for i, hit in enumerate(hits):
        print(f"[DEBUG] Hit {i+1}: id={hit['id']}, score={hit['score']}, payload_keys={list((hit['payload'] or {}).keys())}")

    results = []
    for hit in hits:
        payload = hit["payload"] or {}
        results.append(ChunkResult(
            content=payload.get("content", ""),
            document_id=payload.get("document_id", ""),
            chunk_index=payload.get("chunk_index", -1),
            score=hit["score"],
            page_number=payload.get("page_number", -1),
            payload=payload
        ))
    
    # LLM synthesis
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    context = "\n\n".join([f"Chunk {i+1}: {chunk.content}" for i, chunk in enumerate(results)])
    prompt = (
        "You are a helpful assistant for course materials. "
        "Use ONLY the following context to answer the user's question. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {request.query}\n"
        "Answer:"
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,  # Limit response length to control costs
            temperature=0.1
        )
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"[DEBUG] OpenAI API error: {e}")
        answer = "I'm sorry, I encountered an error while processing your question. Please try again."
    
    return LLMResponse(
        answer=answer,
        chunks=results
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Query service is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 