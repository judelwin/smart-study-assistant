import os
import logging
import uuid
from typing import List
import re
import ssl

import redis
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form, Query
from sqlalchemy.orm import Session
from pinecone import Pinecone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import requests
from fastapi import APIRouter
import boto3
from pydantic import BaseModel

from core.config import settings
from core.database import get_db
from core import models
from core.pdf_parser import extract_text_from_pdf
from core.chunking import chunk_text
from celery_config import celery_app
from shared.storage import upload_file_to_s3, s3_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ClassGPT Ingestion Service",
    description="Handles file uploads, class management, and queues documents for embedding.",
    version="1.0.0",
)

# Production-ready Redis client initialization for Upstash
if ".upstash.io" in settings.REDIS_URL:
    redis_client = redis.from_url(settings.REDIS_URL, ssl_cert_reqs=ssl.CERT_NONE)
else:
    redis_client = redis.from_url(settings.REDIS_URL)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Pinecone configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "classgpt-chunks")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

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

@app.on_event("startup")
def on_startup():
    """
    Check Redis connection on startup.
    """
    try:
        redis_client.ping()
        logger.info("Successfully connected to Redis.")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        # Depending on the use case, you might want to exit the application
        # raise RuntimeError("Failed to connect to Redis") from e


@app.get("/health", status_code=200)
def health_check():
    """
    Health check endpoint to verify service is running.
    """
    return {"status": "ok"}


@app.get("/api/classes", status_code=200)
def get_classes(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """
    Returns a list of all classes.
    """
    classes = db.query(models.Class).filter(models.Class.user_id == user_id).all()
    return classes


@app.post("/api/classes", status_code=201)
def create_class(name: str = Form(...), db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """
    Creates a new class.
    """
    new_class = models.Class(name=name, user_id=user_id)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class


@app.delete("/api/classes/{class_id}", status_code=204)
def delete_class(class_id: uuid.UUID, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """
    Deletes a class and all associated documents, including S3 files.
    """
    db_class = db.query(models.Class).filter(models.Class.id == class_id, models.Class.user_id == user_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    # Delete all S3 files for this class
    docs = db.query(models.Document).filter(models.Document.class_id == class_id).all()
    for doc in docs:
        if doc.s3_url:
            match = re.match(r"https://([^.]+)\.s3\.[^.]+\.amazonaws\.com/(.+)", doc.s3_url)
            if match:
                bucket, key = match.group(1), match.group(2)
                try:
                    s3_client.delete_object(Bucket=bucket, Key=key)
                except Exception as e:
                    print(f"Warning: Failed to delete S3 file {key}: {e}")
    # Associated documents are deleted via CASCADE in the database
    db.delete(db_class)
    db.commit()
    return


@app.post("/api/upload", status_code=200)
async def upload_files(
    class_id: uuid.UUID = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Accepts multiple file uploads for a given class and queues them for processing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were sent.")

    # 1. Verify class exists
    db_class = db.query(models.Class).filter(models.Class.id == class_id, models.Class.user_id == user_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail=f"Class with ID {class_id} not found.")

    processed_files = []
    
    for file in files:
        file_bytes = await file.read()
        
        try:
            # Upload to S3
            s3_url = upload_file_to_s3(file_bytes, file.filename, user_id, class_id)

            # 4. Create a document record in the database
            new_document = models.Document(
                id=uuid.uuid4(),
                class_id=db_class.id,
                filename=file.filename,
                status="pending",
                user_id=user_id,
                s3_url=s3_url,
            )
            db.add(new_document)
            db.commit()
            db.refresh(new_document)

            # 5. Queue the document for processing using Celery
            # We'll use a simple task name that the embedding worker will handle
            celery_app.send_task(
                'tasks.process_document',
                args=[str(new_document.id), s3_url],
                queue='embedding_queue'
            )
            
            processed_files.append(file.filename)
            logger.info(f"Successfully saved and queued document: {file.filename} for class {db_class.name}")

        except Exception as e:
            logger.error(f"Failed to process file {file.filename}. Error: {e}")
            # Optionally, rollback the DB commit or handle partial failure
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Could not save or queue file: {file.filename}"
            )

    response_data = {
        "message": f"Successfully uploaded and queued {len(processed_files)} file(s).",
        "filenames": processed_files,
    }

    return response_data


@app.get("/api/documents", status_code=200)
def get_documents(class_id: uuid.UUID = Query(...), db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """
    Returns a list of all documents for a given class.
    """
    documents = db.query(models.Document).join(models.Class).filter(models.Class.id == class_id, models.Class.user_id == user_id).all()
    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at,
        }
        for doc in documents
    ]


@app.delete("/api/documents/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """
    Deletes a single document by its UUID and removes corresponding embeddings from Pinecone and S3.
    """
    db_doc = db.query(models.Document).join(models.Class).filter(models.Document.id == document_id, models.Class.user_id == user_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Delete S3 file
    if db_doc.s3_url:
        match = re.match(r"https://([^.]+)\.s3\.[^.]+\.amazonaws\.com/(.+)", db_doc.s3_url)
        if match:
            bucket, key = match.group(1), match.group(2)
            try:
                s3_client.delete_object(Bucket=bucket, Key=key)
            except Exception as e:
                print(f"Warning: Failed to delete S3 file {key}: {e}")
    db.delete(db_doc)
    db.commit()
    # Delete corresponding embeddings from Pinecone
    try:
        index = pc.Index(PINECONE_INDEX_NAME)
        index.delete(filter={"document_id": str(document_id)})
        logger.info(f"Successfully deleted embeddings from Pinecone for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to delete embeddings from Pinecone for document {document_id}: {e}")
    return


class BatchPresignRequest(BaseModel):
    document_ids: List[str]

@app.post("/api/presign/batch")
def get_batch_presigned_urls(request: BatchPresignRequest, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Get pre-signed URLs for multiple documents in a single request"""
    # Fetch all documents for the user in a single query
    docs = db.query(models.Document).filter(
        models.Document.id.in_(request.document_ids),
        models.Document.user_id == user_id
    ).all()
    
    # Create a map of document_id to document
    doc_map = {str(doc.id): doc for doc in docs}
    
    # Initialize S3 client once
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_S3_REGION", "us-east-2"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    
    result = {}
    for doc_id in request.document_ids:
        doc = doc_map.get(doc_id)
        if not doc or not doc.s3_url:
            result[doc_id] = None
            continue
            
        try:
            # Parse bucket and key from s3_url
            match = re.match(r"https://([^.]+)\.s3\.[^.]+\.amazonaws\.com/(.+)", doc.s3_url)
            if not match:
                result[doc_id] = None
                continue
                
            bucket, key = match.group(1), match.group(2)
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=3600  # 1 hour
            )
            result[doc_id] = url
        except Exception:
            result[doc_id] = None
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 