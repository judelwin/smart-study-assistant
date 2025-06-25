import os
import fitz  # PyMuPDF
from celery import current_task, Task
from celery_config import celery_app, settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
from embedding_providers import get_embedding_provider
import openai
from qdrant_utils import upsert_embeddings
from core.pdf_parser import extract_text_by_page
from core.chunking import chunk_text
import requests
import boto3
import re
import io

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_s3_file_bytes(s3_url):
    """Download file from S3 and return as bytes"""
    match = re.match(r"https://([^.]+)\.s3\.[^.]+\.amazonaws\.com/(.+)", s3_url)
    if not match:
        raise ValueError("Invalid S3 URL format")
    bucket, key = match.group(1), match.group(2)
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()

def extract_text_by_page_from_bytes(file_bytes):
    """Extract text from PDF bytes using PyMuPDF"""
    try:
        # Open PDF from bytes
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            pages.append((page_num + 1, page_text))  # 1-based page numbers
        doc.close()
        print(f"[CLASSGPT_DEBUG] Extracted {len(pages)} pages from PDF bytes")
        return pages
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Failed to extract text from PDF bytes: {e}")
        return None

@celery_app.task(bind=True)
def process_document(self, document_id: int, file_url: str):
    """
    Process a document: download from S3, extract text, chunk, generate embeddings, and store chunks in database.
    """
    # Download file from S3
    try:
        file_bytes = get_s3_file_bytes(file_url)
        print(f"[CLASSGPT_DEBUG] Downloaded file from S3: {file_url}")
        print(f"[CLASSGPT_DEBUG] File bytes length: {len(file_bytes)}")
        
        # Save file for debugging
        debug_file_path = f"/tmp/debug_upload_{document_id}.pdf"
        with open(debug_file_path, "wb") as f:
            f.write(file_bytes)
        print(f"[CLASSGPT_DEBUG] Saved file to {debug_file_path}")
        
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Failed to download file from S3: {e}")
        raise Exception(f"Failed to download file from S3: {e}")
    
    # Continue with PDF/text extraction using file_bytes
    try:
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Starting document processing...'}
        )
        
        # Get document info including user_id and class_id
        db = SessionLocal()
        try:
            query = text("SELECT user_id, class_id FROM documents WHERE id = :document_id")
            result = db.execute(query, {'document_id': document_id}).fetchone()
            if not result:
                raise Exception(f"Document {document_id} not found")
            user_id, class_id = result
            print(f"[CLASSGPT_DEBUG] Found document {document_id} in class {class_id} for user {user_id}")
        finally:
            db.close()
        
        # Extract text per page
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Extracting text from PDF...'}
        )
        
        print(f"[CLASSGPT_DEBUG] Starting PDF text extraction...")
        pages = extract_text_by_page_from_bytes(file_bytes)
        
        print(f"[CLASSGPT_DEBUG] extract_text_by_page_from_bytes returned: {type(pages)}")
        if pages is None:
            print(f"[CLASSGPT_DEBUG] extract_text_by_page_from_bytes returned None")
            raise Exception("PDF text extraction failed - function returned None")
        
        print(f"[CLASSGPT_DEBUG] Number of pages extracted: {len(pages)}")
        
        # Debug: Print page content previews
        for i, (page_num, page_text) in enumerate(pages):
            text_preview = page_text[:200].replace('\n', '\\n') if page_text else "EMPTY"
            print(f"[CLASSGPT_DEBUG] Page {page_num}: {len(page_text)} chars, preview: {text_preview}")
        
        # Check if any pages have content
        pages_with_content = [page_text.strip() for _, page_text in pages if page_text.strip()]
        print(f"[CLASSGPT_DEBUG] Pages with non-empty content: {len(pages_with_content)}")
        
        if not pages or not pages_with_content:
            print(f"[CLASSGPT_DEBUG] No text content found in any pages")
            raise Exception("No text content extracted from PDF")
        
        # Chunk per page, track page_number
        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': 'Chunking text...'}
        )
        
        print(f"[CLASSGPT_DEBUG] Starting text chunking...")
        all_chunks = []
        all_metadata = []
        for page_number, page_text in pages:
            if not page_text.strip():
                print(f"[CLASSGPT_DEBUG] Skipping empty page {page_number}")
                continue
            page_chunks = chunk_text(page_text)
            print(f"[CLASSGPT_DEBUG] Page {page_number}: created {len(page_chunks)} chunks")
            for chunk in page_chunks:
                all_chunks.append(chunk)
                all_metadata.append({
                    "user_id": str(user_id),
                    "class_id": str(class_id),
                    "document_id": str(document_id),
                    "page_number": page_number
                })
        
        print(f"[CLASSGPT_DEBUG] Total chunks created: {len(all_chunks)}")
        
        if not all_chunks:
            print(f"[CLASSGPT_DEBUG] No chunks created from any pages")
            raise Exception("No text chunks created from PDF")
        
        # Generate embeddings
        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': 'Generating embeddings...'}
        )
        
        print(f"[CLASSGPT_DEBUG] Starting embedding generation for {len(all_chunks)} chunks...")
        embedding_provider = get_embedding_provider()
        embeddings = embedding_provider.embed(all_chunks)
        
        print(f"[CLASSGPT_DEBUG] Generated {len(embeddings)} embeddings for document {document_id}")
        
        # Store chunks in database
        self.update_state(
            state='PROGRESS',
            meta={'current': 70, 'total': 100, 'status': 'Storing chunks in database...'}
        )
        
        print(f"[CLASSGPT_DEBUG] Storing {len(all_chunks)} chunks in database...")
        store_chunks_in_database(document_id, all_chunks)
        
        # Update document status
        self.update_state(
            state='PROGRESS',
            meta={'current': 90, 'total': 100, 'status': 'Updating document status...'}
        )
        
        print(f"[CLASSGPT_DEBUG] Updating document status to 'processed'...")
        update_document_status(document_id, "processed")
        
        print(f"[CLASSGPT_DEBUG] Upserting embeddings to Qdrant...")
        upsert_embeddings(str(document_id), all_chunks, embeddings, all_metadata)
        
        print(f"[CLASSGPT_DEBUG] Document processing completed successfully!")
        return {
            'status': 'success',
            'document_id': document_id,
            'chunks_created': len(all_chunks)
        }
        
    except Exception as e:
        print(f"[CLASSGPT_DEBUG] Document processing failed: {e}")
        # Update document status to failed
        try:
            update_document_status(document_id, "failed")
        except Exception as update_error:
            print(f"[CLASSGPT_DEBUG] Failed to update document status: {update_error}")
        
        raise Exception(f"Document processing failed: {str(e)}")

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF"""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def store_chunks_in_database(document_id: int, chunks: list):
    """Store text chunks in the database"""
    db = SessionLocal()
    try:
        for i, chunk in enumerate(chunks):
            # Insert chunk into database
            query = text("""
                INSERT INTO document_chunks (document_id, chunk_index, content, created_at)
                VALUES (:document_id, :chunk_index, :content, NOW())
            """)
            
            db.execute(query, {
                'document_id': document_id,
                'chunk_index': i,
                'content': chunk
            })
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to store chunks in database: {str(e)}")
    finally:
        db.close()

def update_document_status(document_id: int, status: str):
    """Update document status in database"""
    db = SessionLocal()
    try:
        query = text("""
            UPDATE documents 
            SET status = :status, updated_at = NOW()
            WHERE id = :document_id
        """)
        
        db.execute(query, {
            'document_id': document_id,
            'status': status
        })
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update document status: {str(e)}")
    finally:
        db.close() 