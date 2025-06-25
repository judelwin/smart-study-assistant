#!/usr/bin/env python3
"""
Test script to verify PDF extraction functionality
"""
import os
import sys
import fitz  # PyMuPDF

def test_pdf_extraction_from_bytes():
    """Test PDF extraction from bytes"""
    print("=== Testing PDF Extraction from Bytes ===")
    
    # Test with a simple PDF (you can replace this with your actual PDF)
    test_pdf_path = "/tmp/debug_upload_1.pdf"  # Adjust this path as needed
    
    if not os.path.exists(test_pdf_path):
        print(f"❌ Test PDF not found at {test_pdf_path}")
        print("Please upload a PDF first to create the test file")
        return False
    
    try:
        # Read the PDF file as bytes
        with open(test_pdf_path, "rb") as f:
            file_bytes = f.read()
        
        print(f"✅ Read {len(file_bytes)} bytes from {test_pdf_path}")
        
        # Test extraction using the new function
        from tasks import extract_text_by_page_from_bytes
        
        pages = extract_text_by_page_from_bytes(file_bytes)
        
        if pages is None:
            print("❌ extract_text_by_page_from_bytes returned None")
            return False
        
        print(f"✅ Successfully extracted {len(pages)} pages")
        
        # Print page details
        for i, (page_num, text) in enumerate(pages):
            text_preview = text[:100].replace('\n', '\\n') if text else "EMPTY"
            print(f"  Page {page_num}: {len(text)} chars, preview: {text_preview}")
        
        # Check if any pages have content
        pages_with_content = [text.strip() for _, text in pages if text.strip()]
        print(f"✅ Pages with content: {len(pages_with_content)}")
        
        if not pages_with_content:
            print("⚠️  No pages have text content")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during PDF extraction test: {e}")
        return False

def test_pdf_extraction_from_file():
    """Test PDF extraction from file path"""
    print("\n=== Testing PDF Extraction from File Path ===")
    
    test_pdf_path = "/tmp/debug_upload_1.pdf"  # Adjust this path as needed
    
    if not os.path.exists(test_pdf_path):
        print(f"❌ Test PDF not found at {test_pdf_path}")
        return False
    
    try:
        # Test extraction using the original function
        from core.pdf_parser import extract_text_by_page
        
        pages = extract_text_by_page(test_pdf_path)
        
        if pages is None:
            print("❌ extract_text_by_page returned None")
            return False
        
        print(f"✅ Successfully extracted {len(pages)} pages from file path")
        
        # Print page details
        for i, (page_num, text) in enumerate(pages):
            text_preview = text[:100].replace('\n', '\\n') if text else "EMPTY"
            print(f"  Page {page_num}: {len(text)} chars, preview: {text_preview}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during file path extraction test: {e}")
        return False

if __name__ == "__main__":
    print("Starting PDF extraction tests...\n")
    
    bytes_test = test_pdf_extraction_from_bytes()
    file_test = test_pdf_extraction_from_file()
    
    print(f"\n=== Summary ===")
    print(f"Bytes extraction test: {'✅ PASS' if bytes_test else '❌ FAIL'}")
    print(f"File path extraction test: {'✅ PASS' if file_test else '❌ FAIL'}")
    
    if bytes_test and file_test:
        print("\n🎉 All tests passed! PDF extraction should work.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.") 