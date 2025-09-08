#!/usr/bin/env python3
"""
Quick configuration test for Subnet 46 S3 API
Run this to verify your AWS credentials and S3 bucket access
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.development')

def test_configuration():
    """Test AWS S3 configuration and bucket access"""
    print("🧪 Testing Subnet 46 S3 API Configuration\n")
    
    # Check environment variables
    aws_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    s3_bucket = os.getenv('S3_BUCKET', '1000-resilabs-caleb-dev-bittensor-sn46-datacollection')
    s3_region = os.getenv('S3_REGION', 'us-east-2')
    net_uid = os.getenv('NET_UID', '46')
    
    print(f"📋 Configuration:")
    print(f"   S3 Bucket: {s3_bucket}")
    print(f"   S3 Region: {s3_region}")
    print(f"   NET_UID: {net_uid}")
    print(f"   AWS Access Key: {'✅ Set' if aws_key else '❌ Missing'}")
    print(f"   AWS Secret Key: {'✅ Set' if aws_secret else '❌ Missing'}\n")
    
    if not aws_key or not aws_secret:
        print("❌ AWS credentials not found!")
        print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print("   You can:")
        print("   1. Copy env.development.example to .env.development and edit it")
        print("   2. Set environment variables directly")
        return False
    
    # Test S3 connection
    try:
        print("🔗 Testing S3 connection...")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=s3_region
        )
        
        # Test bucket access
        print(f"📦 Testing bucket access: {s3_bucket}")
        s3_client.head_bucket(Bucket=s3_bucket)
        print("✅ Bucket access successful!")
        
        # Test listing objects (optional)
        try:
            response = s3_client.list_objects_v2(Bucket=s3_bucket, MaxKeys=1)
            print(f"📁 Bucket contents: {'Empty' if response.get('KeyCount', 0) == 0 else f'{response.get(\"KeyCount\", 0)} objects'}")
        except Exception as e:
            print(f"⚠️  Could not list bucket contents: {str(e)}")
        
        # Test presigned URL generation
        print("🔗 Testing presigned URL generation...")
        test_key = "data/hotkey=test/job_id=test/test.txt"
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': s3_bucket, 'Key': test_key},
            ExpiresIn=3600
        )
        print("✅ Presigned URL generation successful!")
        
        return True
        
    except NoCredentialsError:
        print("❌ AWS credentials not found or invalid!")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ Bucket '{s3_bucket}' does not exist!")
        elif error_code == 'AccessDenied':
            print(f"❌ Access denied to bucket '{s3_bucket}'!")
            print("   Check your IAM permissions.")
        else:
            print(f"❌ S3 Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_all_buckets():
    """Test access to all environment buckets"""
    buckets = {
        'Development': '1000-resilabs-caleb-dev-bittensor-sn46-datacollection',
        'Test': '2000-resilabs-test-bittensor-sn46-datacollection',
        'Staging': '3000-resilabs-staging-bittensor-sn46-datacollection',
        'Production': '4000-resilabs-prod-bittensor-sn46-datacollection'
    }
    
    aws_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if not aws_key or not aws_secret:
        print("❌ AWS credentials required for bucket testing")
        return
    
    print("\n🧪 Testing all environment buckets:")
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name='us-east-2'
    )
    
    for env_name, bucket_name in buckets.items():
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ {env_name}: {bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ {env_name}: Bucket does not exist")
            elif error_code == 'AccessDenied':
                print(f"⚠️  {env_name}: Access denied (check permissions)")
            else:
                print(f"❌ {env_name}: {error_code}")

if __name__ == "__main__":
    success = test_configuration()
    
    if success:
        print("\n🎉 Configuration test successful!")
        print("   Your API should work with the current configuration.")
        
        # Test all buckets if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--all-buckets":
            test_all_buckets()
            
        print("\n📚 Next steps:")
        print("   1. Run the API: python -m uvicorn s3_storage_api.server:app --reload")
        print("   2. Test health: curl http://localhost:8000/healthcheck")
        print("   3. View docs: http://localhost:8000/docs")
        print("   4. Deploy to AWS (see DEPLOYMENT.md)")
        
    else:
        print("\n❌ Configuration test failed!")
        print("   Please fix the issues above before deploying.")
        sys.exit(1)
