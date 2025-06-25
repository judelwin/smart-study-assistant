#!/usr/bin/env python3
import os
import boto3
import re
from botocore.exceptions import ClientError, NoCredentialsError

def test_s3_credentials():
    """Test if AWS credentials are properly configured"""
    print("=== Testing AWS S3 Credentials ===")
    
    # Check environment variables
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket = os.getenv("AWS_S3_BUCKET")
    region = os.getenv("AWS_S3_REGION", "us-east-2")
    
    print(f"AWS_ACCESS_KEY_ID: {'SET' if aws_access_key else 'NOT_SET'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'SET' if aws_secret_key else 'NOT_SET'}")
    print(f"AWS_S3_BUCKET: {bucket or 'NOT_SET'}")
    print(f"AWS_S3_REGION: {region}")
    
    if not all([aws_access_key, aws_secret_key, bucket]):
        print("❌ Missing required AWS environment variables")
        return False
    
    try:
        # Test S3 client creation
        s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )
        print("✅ S3 client created successfully")
        
        # Test bucket access
        try:
            s3_client.head_bucket(Bucket=bucket)
            print(f"✅ Successfully accessed bucket: {bucket}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"❌ Bucket {bucket} does not exist")
            elif error_code == '403':
                print(f"❌ Access denied to bucket {bucket}")
            else:
                print(f"❌ Error accessing bucket {bucket}: {error_code}")
            return False
        
        # Test listing objects (limited to 1 to avoid long output)
        try:
            response = s3_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
            print(f"✅ Successfully listed objects in bucket {bucket}")
            if 'Contents' in response:
                print(f"   Found {len(response['Contents'])} object(s) (showing first 1)")
            else:
                print("   Bucket appears to be empty")
        except ClientError as e:
            print(f"❌ Error listing objects: {e}")
            return False
            
        return True
        
    except NoCredentialsError:
        print("❌ No AWS credentials found")
        return False
    except Exception as e:
        print(f"❌ Error creating S3 client: {e}")
        return False

def test_s3_download_function():
    """Test the S3 download function from tasks.py"""
    print("\n=== Testing S3 Download Function ===")
    
    # Import the function from tasks
    try:
        from tasks import get_s3_file_bytes
        print("✅ Successfully imported get_s3_file_bytes function")
    except ImportError as e:
        print(f"❌ Failed to import get_s3_file_bytes: {e}")
        return False
    
    # Test with a sample URL (this won't actually download, just test the regex)
    test_url = "https://test-bucket.s3.us-east-2.amazonaws.com/test-file.pdf"
    try:
        match = re.match(r"https://([^.]+)\.s3\.[^.]+\.amazonaws\.com/(.+)", test_url)
        if match:
            bucket, key = match.group(1), match.group(2)
            print(f"✅ URL parsing works: bucket={bucket}, key={key}")
        else:
            print("❌ URL parsing failed")
            return False
    except Exception as e:
        print(f"❌ Error testing URL parsing: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Starting S3 access tests...\n")
    
    creds_ok = test_s3_credentials()
    download_ok = test_s3_download_function()
    
    print(f"\n=== Summary ===")
    print(f"Credentials test: {'✅ PASS' if creds_ok else '❌ FAIL'}")
    print(f"Download function test: {'✅ PASS' if download_ok else '❌ FAIL'}")
    
    if creds_ok and download_ok:
        print("\n🎉 All tests passed! S3 access should work.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.") 