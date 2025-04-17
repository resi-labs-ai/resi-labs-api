"""
S3 Authentication Server for Data Universe
Provides secure folder-based access for miners and validators
"""
import os
import time
import base64
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import boto3
from botocore.config import Config

from s3_storage_api.utils.redis_utils import RedisClient
from s3_storage_api.utils.bt_utils import verify_commitment


# Configuration
S3_BUCKET = os.getenv('S3_BUCKET', 'data-universe-storage')
S3_REGION = os.getenv('S3_REGION', 'us-east-1')
SERVER_PORT = int(os.getenv('PORT', '8000'))
COMMITMENT_VALIDITY_SECONDS = 60  # 1 minute window for authentication

# Rate limiting configuration
DAILY_LIMIT_PER_MINER = 20
DAILY_LIMIT_PER_VALIDATOR = 30
TOTAL_DAILY_LIMIT = 2000

# Initialize FastAPI app
app = FastAPI(
    title="S3 Auth Server for Data Universe",
    description="Authentication server for S3 storage in Data Universe subnet",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
redis_client = RedisClient()

# Initialize S3 client
s3_client = boto3.client(
    's3',
    region_name=S3_REGION,
    config=Config(signature_version='s3v4')
)

# Pydantic models
class MinerFolderAccessRequest(BaseModel):
    coldkey: str
    hotkey: str
    source: str = "x"  # Default to X/Twitter
    netuid: int = 13   # Default to Data Universe subnet
    network: str = "finney"  # Default to mainnet
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    expiry: Optional[int] = None

class ValidatorAccessRequest(BaseModel):
    validator_hotkey: str
    netuid: int = 13   # Default to Data Universe subnet
    network: str = "finney"  # Default to mainnet
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    expiry: Optional[int] = None

# Helper functions
def check_rate_limit(key: str, daily_limit: int) -> Tuple[bool, Optional[str]]:
    """Check if an entity has exceeded their daily rate limit"""
    today = time.strftime('%Y-%m-%d')

    # Check global limit first
    global_key = f"GLOBAL:{today}"
    global_count = redis_client.get_counter(global_key)

    if global_count >= TOTAL_DAILY_LIMIT:
        return False, f"Daily request quota exceeded for all users. Please try again tomorrow."

    # Then check entity's limit
    entity_key = f"{key}:{today}"
    entity_count = redis_client.get_counter(entity_key)

    if entity_count >= daily_limit:
        return False, f"Daily request quota of {daily_limit} exceeded. Please try again tomorrow."

    # Increment counters
    redis_client.increment_counter(entity_key)
    redis_client.increment_counter(global_key)

    return True, None

def generate_folder_upload_policy(bucket: str, folder_prefix: str, expiry_hours: int = 24) -> Dict:
    """Generate a POST policy for uploading multiple files to a folder"""
    # Calculate expiration time
    expiration = datetime.utcnow() + timedelta(hours=expiry_hours)

    # Create policy document with enhanced security
    policy = {
        "expiration": expiration.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "conditions": [
            # Restrict to specific bucket only
            {"bucket": bucket},

            # Restrict to specific folder prefix
            ["starts-with", "$key", folder_prefix],

            # Ensure files are private
            {"acl": "private"},

            # File size limits - minimum 1KB, maximum 5GB
            ["content-length-range", 1024, 5368709120],

            # Storage class restriction
            {"x-amz-storage-class": "STANDARD"}
        ]
    }

    # Get AWS credentials
    credentials = s3_client.meta.config.credentials

    # Convert policy to base64
    policy_json = json.dumps(policy).encode('utf-8')
    policy_base64 = base64.b64encode(policy_json).decode('utf-8')

    # Create signature
    signature = base64.b64encode(
        hmac.new(
            credentials.secret_key.encode('utf-8'),
            policy_base64.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')

    # Generate a direct presigned URL for listing the folder contents
    list_url = s3_client.generate_presigned_url(
        'list_objects_v2',
        Params={
            'Bucket': bucket,
            'Prefix': folder_prefix
        },
        ExpiresIn=expiry_hours * 3600
    )

    return {
        "url": f"https://{bucket}.s3.amazonaws.com/",
        "folder": folder_prefix,
        "expiry": expiration.isoformat(),
        "expiry_seconds": expiry_hours * 3600,
        "fields": {
            "acl": "private",
            "policy": policy_base64,
            "AWSAccessKeyId": credentials.access_key,
            "signature": signature,
            "x-amz-storage-class": "STANDARD"
        },
        "list_url": list_url,
        "instructions": "Use this policy with a POST request to upload any file to your folder."
    }


def generate_validator_access_urls(validator_hotkey: str, expiry_hours: int = 24) -> Dict:
    """Generate a comprehensive set of presigned URLs for validator access"""
    # Calculate expiration time
    expiration = datetime.utcnow() + timedelta(hours=expiry_hours)
    expiry_seconds = expiry_hours * 3600

    # Dictionary to hold all access URLs
    access_urls = {
        'global': {},
        'sources': {},
        'miners': {}
    }

    # Global bucket access URLs
    access_urls['global']['list_all_data'] = s3_client.generate_presigned_url(
        'list_objects_v2',
        Params={
            'Bucket': S3_BUCKET,
            'Prefix': 'data/',
            'Delimiter': '/'
        },
        ExpiresIn=expiry_seconds
    )

    # Source-specific URLs
    for source in ['x', 'reddit']:
        source_prefix = f'data/{source}/'

        # List all miners for this source
        list_miners_url = s3_client.generate_presigned_url(
            'list_objects_v2',
            Params={
                'Bucket': S3_BUCKET,
                'Prefix': source_prefix,
                'Delimiter': '/'
            },
            ExpiresIn=expiry_seconds
        )

        access_urls['sources'][source] = {
            'list_miners': list_miners_url,
            'prefix': source_prefix
        }

    # Get a list of miners to generate miner-specific URLs
    try:
        # Find miners by listing prefixes
        all_miners = set()
        for source in ['x', 'reddit']:
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=f'data/{source}/',
                Delimiter='/'
            )

            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    parts = prefix['Prefix'].split('/')
                    if len(parts) >= 3:
                        coldkey = parts[2]
                        all_miners.add(coldkey)

        # Generate URLs for each miner
        for coldkey in all_miners:
            miner_urls = {}
            for source in ['x', 'reddit']:
                folder_path = f'data/{source}/{coldkey}/'

                # List URL
                list_url = s3_client.generate_presigned_url(
                    'list_objects_v2',
                    Params={
                        'Bucket': S3_BUCKET,
                        'Prefix': folder_path
                    },
                    ExpiresIn=expiry_seconds
                )

                # Batch get URL template
                batch_get_template = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': S3_BUCKET,
                        'Key': folder_path + "OBJECT_KEY_PLACEHOLDER"
                    },
                    ExpiresIn=expiry_seconds
                )
                batch_get_template = batch_get_template.replace("OBJECT_KEY_PLACEHOLDER", "")

                miner_urls[source] = {
                    'list_files': list_url,
                    'get_template': batch_get_template,
                    'folder': folder_path
                }

            access_urls['miners'][coldkey] = miner_urls
    except Exception as e:
        print(f"Error listing miners: {str(e)}")

    return {
        'bucket': S3_BUCKET,
        'region': S3_REGION,
        'validator_hotkey': validator_hotkey,
        'expiry': expiration.isoformat(),
        'expiry_seconds': expiry_seconds,
        'urls': access_urls,
        'instructions': 'Use these URLs to access miner data across the platform.'
    }

# MINER ENDPOINTS
@app.post("/get-folder-access")
async def get_folder_access(request: MinerFolderAccessRequest):
    """Endpoint to get write access to a folder for a miner"""
    try:
        coldkey = request.coldkey
        hotkey = request.hotkey
        source = request.source
        timestamp = request.timestamp
        netuid = request.netuid
        network = request.network
        expiry = request.expiry or (timestamp + 3600 * 24)  # Default 24 hour validity

        # Folder path based on source and miner coldkey
        folder_path = f"data/{source}/{coldkey}/"

        # Check rate limit
        is_allowed, error_message = check_rate_limit(hotkey, DAILY_LIMIT_PER_MINER)
        if not is_allowed:
            raise HTTPException(status_code=429, detail=error_message)

        # Validate timestamp
        current_time = int(time.time())
        if current_time > expiry:
            raise HTTPException(status_code=400, detail="Request expired")

        # Ensure request isn't too old
        if current_time - timestamp > 300:  # 5 minutes max
            raise HTTPException(status_code=400, detail="Request timestamp too old")

        # Ensure request timestamp is not in the future
        if timestamp > current_time + 60:  # Allow 1 minute clock skew
            raise HTTPException(status_code=400, detail="Request timestamp is in the future")

        # Verify blockchain commitment (within 1 minute window)
        expected_commitment = f"s3:access:{coldkey}:{source}:{timestamp}"
        if not verify_commitment(hotkey, expected_commitment, netuid, network, COMMITMENT_VALIDITY_SECONDS):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired blockchain commitment. Ensure you commit to chain and make request within 1 minute."
            )

        # Generate folder upload policy
        folder_policy = generate_folder_upload_policy(S3_BUCKET, folder_path, expiry_hours=24)

        # Generate direct presigned URL for listing
        get_url = s3_client.generate_presigned_url(
            'list_objects_v2',
            Params={
                'Bucket': S3_BUCKET,
                'Prefix': folder_path
            },
            ExpiresIn=3600 * 24
        )

        return {
            'folder_path': folder_path,
            'policy': folder_policy,
            'list_url': get_url,
            'expiry': datetime.fromtimestamp(expiry).isoformat(),
            'instructions': 'Use this policy to upload multiple files to your folder'
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# VALIDATOR ENDPOINTS
@app.post("/get-validator-access")
async def get_validator_access(request: ValidatorAccessRequest):
    """Endpoint to get comprehensive bucket read access for validators"""
    try:
        validator_hotkey = request.validator_hotkey
        timestamp = request.timestamp
        netuid = request.netuid
        network = request.network
        expiry = request.expiry or (timestamp + 3600 * 24)  # 24 hour validity

        # Check validator rate limit
        is_allowed, error_message = check_rate_limit(validator_hotkey, DAILY_LIMIT_PER_VALIDATOR)
        if not is_allowed:
            raise HTTPException(status_code=429, detail=error_message)

        # Validate timestamp
        current_time = int(time.time())
        if current_time > expiry:
            raise HTTPException(status_code=400, detail="Request expired")

        # Ensure request isn't too old
        if current_time - timestamp > 300:  # 5 minutes max
            raise HTTPException(status_code=400, detail="Request timestamp too old")

        # Ensure request timestamp is not in the future
        if timestamp > current_time + 60:  # Allow 1 minute clock skew
            raise HTTPException(status_code=400, detail="Request timestamp is in the future")

        # Verify blockchain commitment (within 1 minute window)
        expected_commitment = f"s3:validator:access:{timestamp}"
        if not verify_commitment(validator_hotkey, expected_commitment, netuid, network, COMMITMENT_VALIDITY_SECONDS):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired blockchain commitment. Ensure you commit to chain and make request within 1 minute."
            )

        # Generate comprehensive validator access URLs
        access_data = generate_validator_access_urls(
            validator_hotkey=validator_hotkey,
            expiry_hours=24
        )

        return access_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GENERAL ENDPOINTS
@app.get("/healthcheck")
async def health_check():
    """Simple health check endpoint"""
    return {
        'status': 'ok',
        'timestamp': time.time(),
        'bucket': S3_BUCKET,
        'region': S3_REGION
    }

@app.get("/commitment-formats")
async def commitment_formats():
    """Return the expected format for blockchain commitments"""
    return {
        'miner_format': "s3:access:{coldkey}:{source}:{timestamp}",
        'validator_format': "s3:validator:access:{timestamp}",
        'example_miner': "s3:access:5F3sa2TJAEsVN1Xk3SHJRLmSQLBGCgEFrH8PpKwSuHk3g2dP:x:1682345678",
        'example_validator': "s3:validator:access:1682345678",
        'important_note': "You must make the API request within 1 minute of creating the blockchain commitment",
        'instructions': (
            "1. Generate a timestamp (current Unix time in seconds)\n"
            "2. Commit the formatted string to blockchain\n"
            "3. Immediately request access from this API using the same timestamp"
        )
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT, reload=True)