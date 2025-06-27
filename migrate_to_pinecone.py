#!/usr/bin/env python3
"""
Migration script to help you switch from Qdrant to Pinecone.
This script will help you set up Pinecone and test the connection.
"""

import os
import pinecone
from typing import List, Dict

def setup_pinecone():
    """Set up Pinecone index with the correct configuration"""
    
    # Get environment variables
    api_key = os.getenv("PINECONE_API_KEY")
    environment = os.getenv("PINECONE_ENVIRONMENT")
    index_name = os.getenv("PINECONE_INDEX_NAME", "classgpt-chunks")
    
    if not api_key or not environment:
        print("❌ Error: PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set")
        print("Please set these environment variables:")
        print("  PINECONE_API_KEY=your_api_key_here")
        print("  PINECONE_ENVIRONMENT=gcp-starter  # or your environment")
        return False
    
    print(f"🔑 Pinecone API Key: {'SET' if api_key else 'NOT SET'}")
    print(f"🌍 Pinecone Environment: {environment}")
    print(f"📊 Index Name: {index_name}")
    
    try:
        # Initialize Pinecone
        pinecone.init(api_key=api_key, environment=environment)
        print("✅ Successfully initialized Pinecone client")
        
        # Check if index exists
        existing_indexes = pinecone.list_indexes()
        print(f"📋 Existing indexes: {existing_indexes}")
        
        if index_name in existing_indexes:
            print(f"✅ Index '{index_name}' already exists")
            return True
        else:
            print(f"🔨 Creating index '{index_name}'...")
            pinecone.create_index(
                name=index_name,
                dimension=1536,  # OpenAI ada-002 embedding dimension
                metric="cosine",
                metadata_config={
                    "indexed": ["user_id", "class_id", "document_id", "chunk_index"]
                }
            )
            print(f"✅ Successfully created index '{index_name}'")
            return True
            
    except Exception as e:
        print(f"❌ Error setting up Pinecone: {e}")
        return False

def test_pinecone_operations():
    """Test basic Pinecone operations"""
    
    index_name = os.getenv("PINECONE_INDEX_NAME", "classgpt-chunks")
    
    try:
        # Get the index
        index = pinecone.Index(index_name)
        print(f"✅ Successfully connected to index '{index_name}'")
        
        # Test upsert
        test_vector = [0.1] * 1536  # Dummy vector
        test_metadata = {
            "user_id": "test_user",
            "class_id": "test_class",
            "document_id": "test_doc",
            "chunk_index": 0,
            "content": "This is a test chunk"
        }
        
        index.upsert(
            vectors=[{
                "id": "test_vector_1",
                "values": test_vector,
                "metadata": test_metadata
            }]
        )
        print("✅ Successfully upserted test vector")
        
        # Test query
        results = index.query(
            vector=test_vector,
            top_k=1,
            include_metadata=True
        )
        print(f"✅ Successfully queried index, got {len(results.matches)} results")
        
        # Test filter
        filtered_results = index.query(
            vector=test_vector,
            top_k=1,
            filter={"user_id": "test_user"},
            include_metadata=True
        )
        print(f"✅ Successfully queried with filter, got {len(filtered_results.matches)} results")
        
        # Clean up test data
        index.delete(ids=["test_vector_1"])
        print("✅ Successfully deleted test vector")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Pinecone operations: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Pinecone Migration Script")
    print("=" * 50)
    
    # Step 1: Set up Pinecone
    print("\n📋 Step 1: Setting up Pinecone...")
    if not setup_pinecone():
        print("❌ Failed to set up Pinecone. Please check your credentials.")
        return
    
    # Step 2: Test operations
    print("\n🧪 Step 2: Testing Pinecone operations...")
    if not test_pinecone_operations():
        print("❌ Failed to test Pinecone operations.")
        return
    
    print("\n✅ Migration setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Update your .env file with Pinecone credentials:")
    print("   PINECONE_API_KEY=your_api_key_here")
    print("   PINECONE_ENVIRONMENT=gcp-starter")
    print("   PINECONE_INDEX_NAME=classgpt-chunks")
    print("\n2. Restart your services:")
    print("   docker-compose down")
    print("   docker-compose up -d")
    print("\n3. Test your application with a new document upload")

if __name__ == "__main__":
    main() 