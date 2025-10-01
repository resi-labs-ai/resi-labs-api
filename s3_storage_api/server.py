import os
import time
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

import boto3
from botocore.config import Config
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from s3_storage_api.utils.redis_utils import RedisClient
from s3_storage_api.utils.bt_utils import verify_signature, verify_validator_status
from s3_storage_api.utils.metagraph_syncer import MetagraphSyncer
from s3_storage_api.utils.bt_utils_cached import (
    verify_signature_cached,
    verify_validator_status_cached
)
from s3_storage_api.database import get_db, check_database_health, init_database
from s3_storage_api.services.zipcode_service import ZipcodeService
from s3_storage_api.services.epoch_manager import EpochManager
from s3_storage_api.services.validator_s3_service import ValidatorS3Service
import bittensor as bt

load_dotenv()

# Configuration
S3_BUCKET = os.getenv('S3_BUCKET', '1000-resilabs-caleb-dev-bittensor-sn46-datacollection')
S3_REGION = os.getenv('S3_REGION', 'us-east-2')
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "your-access-key-here")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "your-secret-key-here")
SERVER_PORT = int(os.getenv('PORT', '8000'))
BT_NETWORK = os.getenv("BT_NETWORK", "finney")
NET_UID = int(os.getenv('NET_UID', '46'))
COMMITMENT_VALIDITY_SECONDS = 60

DAILY_LIMIT_PER_MINER = int(os.getenv('DAILY_LIMIT_PER_MINER', '20'))
DAILY_LIMIT_PER_VALIDATOR = int(os.getenv('DAILY_LIMIT_PER_VALIDATOR', '10000'))
TOTAL_DAILY_LIMIT = int(os.getenv('TOTAL_DAILY_LIMIT', '200000'))

# Timeout configurations
VALIDATOR_VERIFICATION_TIMEOUT = 120  # 2 minutes
SIGNATURE_VERIFICATION_TIMEOUT = 60  # 1 minute
S3_OPERATION_TIMEOUT = 60  # 1 minute

# Metagraph sync configuration
METAGRAPH_SYNC_INTERVAL = 300  # 5 minutes

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Resi Labs API - Subnet 46",
    description="S3 Authentication and Zipcode Assignment API for Bittensor Subnet 46",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = RedisClient()

# Custom OpenAPI configuration
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Resi Labs API - Subnet 46",
        version="2.0.0",
        description="""
# Resi Labs API for Bittensor Subnet 46

This API provides two main services:

## 🔐 S3 Authentication Service
- **Miners**: Get S3 upload credentials for real estate data
- **Validators**: Get read access to miner data for validation

## 🗺️ Zipcode Assignment Service  
- **Competitive Mining**: 4-hour epochs with zipcode assignments
- **Anti-Gaming**: Nonce-based security and honeypot detection
- **Validator Uploads**: S3 access for storing winning validation results

## Authentication
All endpoints require bittensor hotkey signatures:
1. Create commitment string (format specified per endpoint)
2. Sign with your hotkey: `signature = hotkey.sign(commitment.encode()).hex()`
3. Include signature in request

## Rate Limiting
- **Miners**: 10 zipcode requests/minute, 20 S3 requests/day
- **Validators**: 20 historical requests/hour, 5 S3 uploads/hour
- **Public**: 30 stats requests/minute

## Epochs
- **Duration**: 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
- **Target**: 10,000 ±10% listings per epoch
- **States**: PA, NJ prioritized (configurable)
        """,
        routes=app.routes,
        tags=[
            {
                "name": "Zipcode Assignments",
                "description": "Get zipcode assignments for competitive mining"
            },
            {
                "name": "Validator S3 Access", 
                "description": "S3 upload access for validators to store results"
            },
            {
                "name": "S3 Authentication",
                "description": "Original S3 authentication for miners and validators"
            },
            {
                "name": "System Health",
                "description": "Health checks and system statistics"
            }
        ]
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BittensorSignature": {
            "type": "apiKey",
            "in": "header", 
            "name": "Authorization",
            "description": "Bittensor hotkey signature. Format: Bearer {signature_hex}"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Resi Labs API Documentation",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
    )

# Initialize MetagraphSyncer for cached blockchain queries
logger.info("Initializing MetagraphSyncer...")
try:
    subtensor = bt.subtensor(network=BT_NETWORK)
    metagraph_syncer = MetagraphSyncer(subtensor, config={NET_UID: METAGRAPH_SYNC_INTERVAL})
    metagraph_syncer.do_initial_sync()
    metagraph_syncer.start()
    logger.info(f"MetagraphSyncer initialized successfully for netuid {NET_UID}")
except Exception as e:
    logger.error(f"Failed to initialize MetagraphSyncer: {str(e)}")
    logger.error("Falling back to original bt_utils functions")
    metagraph_syncer = None
    subtensor = None

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=S3_REGION,
    config=Config(
        signature_version='s3v4',
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        connect_timeout=10,
        read_timeout=30
    )
)

# Initialize zipcode assignment services
zipcode_service = ZipcodeService()
epoch_manager = EpochManager(zipcode_service)
validator_s3_service = ValidatorS3Service()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks"""
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Don't fail startup - allow API to run without zipcode features
    
    # Start background epoch management
    try:
        from s3_storage_api.database import AsyncSessionLocal
        await epoch_manager.start_background_management(AsyncSessionLocal)
        logger.info("Background epoch management started")
    except Exception as e:
        logger.error(f"Failed to start background epoch management: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    try:
        await epoch_manager.stop_background_management()
        logger.info("Background tasks stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


class MinerFolderAccessRequest(BaseModel):
    coldkey: str
    hotkey: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    signature: str  # HEX string
    expiry: Optional[int] = None


class ValidatorAccessRequest(BaseModel):
    hotkey: str
    signature: str  # HEX string
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    expiry: Optional[int] = None
    miner_hotkey: Optional[str] = None

# New Pydantic models for zipcode endpoints
class ZipcodeAssignmentRequest(BaseModel):
    hotkey: str
    signature: str  # HEX string
    timestamp: int = Field(default_factory=lambda: int(time.time()))

class ValidatorS3UploadRequest(BaseModel):
    hotkey: str
    signature: str  # HEX string
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    purpose: str = "epoch_validation_results"
    epoch_id: str
    estimated_data_size_mb: Optional[int] = 25
    retention_days: Optional[int] = 90

class MinerStatusRequest(BaseModel):
    hotkey: str
    signature: str  # HEX string
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    epoch_id: str
    nonce: str
    status: str  # "in_progress", "completed", "failed"
    listings_scraped: Optional[int] = None
    zipcodes_completed: Optional[List[dict]] = None
    s3_upload_complete: Optional[bool] = False
    s3_upload_timestamp: Optional[str] = None


# Lightweight monitoring - just counters
class SimpleMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.requests = 0
        self.errors = 0
        self.timeouts = 0

    def count_request(self, error=False, timeout=False):
        self.requests += 1
        if error:
            self.errors += 1
        if timeout:
            self.timeouts += 1

    def get_stats(self):
        uptime = time.time() - self.start_time
        return {
            'uptime_hours': round(uptime / 3600, 2),
            'total_requests': self.requests,
            'total_errors': self.errors,
            'total_timeouts': self.timeouts,
            'error_rate': self.errors / self.requests if self.requests > 0 else 0,
            'timeout_rate': self.timeouts / self.requests if self.requests > 0 else 0,
            'requests_per_hour': self.requests / (uptime / 3600) if uptime > 0 else 0
        }


monitor = SimpleMonitor()


# Simple middleware to count requests
@app.middleware("http")
async def count_requests(request: Request, call_next):
    try:
        response = await call_next(request)
        monitor.count_request(error=response.status_code >= 400)
        return response
    except Exception as e:
        monitor.count_request(error=True)
        raise


# Optimized validation functions using cached metagraph
async def verify_validator_status_with_timeout(hotkey: str, netuid: int, network: str) -> bool:
    """Verify validator status with cached metagraph and timeout fallback"""
    try:
        # Try cached version first (should be ~1ms)
        if metagraph_syncer is not None:
            try:
                metagraph = metagraph_syncer.get_metagraph(netuid)
                return verify_validator_status_cached(hotkey, metagraph)
            except Exception as e:
                logger.warning(f"Cached validator verification failed for {hotkey}: {str(e)}, falling back to blockchain")
        
        # Fallback to original method with timeout protection
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, verify_validator_status, hotkey, netuid, network
            ),
            timeout=VALIDATOR_VERIFICATION_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.error(f"Validator verification timeout for {hotkey}")
        monitor.count_request(timeout=True)
        return False
    except Exception as e:
        logger.error(f"Validator verification error for {hotkey}: {str(e)}")
        return False


async def verify_signature_with_timeout(commitment: str, signature: str, hotkey: str, netuid: int,
                                        network: str) -> bool:
    """Verify signature with cached metagraph and timeout fallback"""
    try:
        # Try cached version first (should be ~1ms)
        if metagraph_syncer is not None:
            try:
                metagraph = metagraph_syncer.get_metagraph(netuid)
                return verify_signature_cached(commitment, signature, hotkey, metagraph)
            except Exception as e:
                logger.warning(f"Cached signature verification failed for {hotkey}: {str(e)}, falling back to blockchain")
        
        # Fallback to original method with timeout protection
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, verify_signature, commitment, signature, hotkey, netuid, network
            ),
            timeout=SIGNATURE_VERIFICATION_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.error(f"Signature verification timeout for {hotkey}")
        monitor.count_request(timeout=True)
        return False
    except Exception as e:
        logger.error(f"Signature verification error for {hotkey}: {str(e)}")
        return False


def check_rate_limit(key: str, daily_limit: int) -> Tuple[bool, Optional[str]]:
    today = time.strftime('%Y-%m-%d')
    global_key = f"GLOBAL:{today}"
    global_count = redis_client.get_counter(global_key)
    if global_count >= TOTAL_DAILY_LIMIT:
        return False, "Global request limit reached."
    entity_key = f"{key}:{today}"
    entity_count = redis_client.get_counter(entity_key)
    if entity_count >= daily_limit:
        return False, f"Daily limit of {daily_limit} exceeded."
    redis_client.increment_counter(entity_key)
    redis_client.increment_counter(global_key)
    return True, None


def generate_folder_upload_policy(bucket: str, folder_prefix: str, expiry_hours: int = 3) -> Dict:
    """Generate upload policy for job-based folder structure"""
    fields = {
        "acl": "private",
        "x-amz-storage-class": "STANDARD"
    }

    conditions = [
        {"acl": "private"},
        ["starts-with", "$key", folder_prefix],
        ["content-length-range", 1024, 5368709120],
        {"x-amz-storage-class": "STANDARD"}
    ]

    post = s3_client.generate_presigned_post(
        Bucket=bucket,
        Key=f"{folder_prefix}${{filename}}",
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=expiry_hours * 3600
    )

    post["url"] = f"https://{bucket}.s3.{S3_REGION}.amazonaws.com"
    return post


def generate_validator_access_urls(validator_hotkey: str, expiry_hours: int = 24) -> Dict:
    """Generate validator access URLs for job-based structure"""
    expiration = datetime.utcnow() + timedelta(hours=expiry_hours)
    expiry_seconds = expiry_hours * 3600
    urls = {'global': {}, 'miners': {}}

    # Global listing - all data (with data/ prefix)
    urls['global']['list_all_data'] = s3_client.generate_presigned_url(
        'list_objects_v2',
        Params={'Bucket': S3_BUCKET, 'Prefix': 'data/hotkey='},
        ExpiresIn=expiry_seconds
    )

    # List all miners (hotkeys) (with data/ prefix)
    urls['miners']['list_all_miners'] = s3_client.generate_presigned_url(
        'list_objects_v2',
        Params={'Bucket': S3_BUCKET, 'Prefix': 'data/hotkey=', 'Delimiter': '/'},
        ExpiresIn=expiry_seconds
    )

    return {
        'bucket': S3_BUCKET,
        'region': S3_REGION,
        'validator_hotkey': validator_hotkey,
        'expiry': expiration.isoformat(),
        'expiry_seconds': expiry_seconds,
        'urls': urls,
        'structure_info': {
            'folder_structure': 'data/hotkey={hotkey_id}/job_id={job_id}/',
            'description': 'Job-based folder structure with explicit hotkey and job_id labels under data/ prefix'
        }
    }


# ============================================================================
# NEW ZIPCODE ASSIGNMENT ENDPOINTS
# ============================================================================

@app.get("/api/v1/zipcode-assignments/current", tags=["Zipcode Assignments"])
async def get_current_zipcode_assignment(
    hotkey: str,
    signature: str,
    timestamp: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current zipcode assignments for miners.
    
    **Authentication**: Requires valid bittensor hotkey signature
    **Rate Limit**: 10 requests per minute per hotkey
    **Commitment Format**: `zipcode:assignment:current:{timestamp}`
    """
    try:
        # Basic timestamp validation
        now = int(time.time())
        if abs(now - timestamp) > 300:  # 5 minutes tolerance
            raise HTTPException(status_code=400, detail="Invalid timestamp")
        
        # Light rate limiting - 10 requests per minute per hotkey
        rate_limit_key = f"zipcode_current:{hotkey}"
        current_count = redis_client.get_counter(rate_limit_key)
        if current_count >= 10:
            raise HTTPException(status_code=429, detail="Rate limit exceeded: 10 requests per minute")
        redis_client.increment_counter(rate_limit_key, expire=60)
        
        # Verify signature (miners need to be registered)
        commitment = f"zipcode:assignment:current:{timestamp}"
        signature_valid = await verify_signature_with_timeout(commitment, signature, hotkey, NET_UID, BT_NETWORK)
        if not signature_valid:
            logger.warning(f"ZIPCODE ASSIGNMENT - Invalid signature: {hotkey}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Get current epoch
        current_epoch = await epoch_manager.get_current_epoch(db)
        if not current_epoch:
            raise HTTPException(status_code=404, detail="No current epoch available")
        
        # Build response
        zipcodes_data = []
        for assignment in current_epoch.assignments:
            zipcodes_data.append({
                "zipcode": assignment.zipcode,
                "expected_listings": assignment.expected_listings,
                "state": assignment.state,
                "city": assignment.city,
                "county": assignment.county,
                "market_tier": assignment.market_tier,
                "geographic_region": assignment.geographic_region
            })
        
        return {
            "success": True,
            "epoch_id": current_epoch.id,
            "epoch_start": current_epoch.start_time.isoformat(),
            "epoch_end": current_epoch.end_time.isoformat(),
            "nonce": current_epoch.nonce,
            "target_listings": current_epoch.target_listings,
            "tolerance_percent": current_epoch.tolerance_percent,
            "submission_deadline": current_epoch.end_time.isoformat(),
            "zipcodes": zipcodes_data,
            "metadata": {
                "total_expected_listings": current_epoch.total_expected_listings,
                "zipcode_count": len(zipcodes_data),
                "algorithm_version": current_epoch.algorithm_version,
                "selection_seed": current_epoch.selection_seed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_zipcode_assignment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/zipcode-assignments/epoch/{epoch_id}", tags=["Zipcode Assignments"])
async def get_historical_epoch(
    epoch_id: str,
    hotkey: str,
    signature: str,
    timestamp: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical epoch assignments for validators.
    
    **Authentication**: Requires validator status + signature
    **Rate Limit**: 20 requests per hour per validator
    **Commitment Format**: `zipcode:validation:{epoch_id}:{timestamp}`
    """
    try:
        # Basic timestamp validation
        now = int(time.time())
        if abs(now - timestamp) > 300:
            raise HTTPException(status_code=400, detail="Invalid timestamp")
        
        # Verify validator status
        validator_status = await verify_validator_status_with_timeout(hotkey, NET_UID, BT_NETWORK)
        if not validator_status:
            logger.warning(f"HISTORICAL EPOCH ACCESS DENIED: {hotkey} - not a validator")
            raise HTTPException(status_code=403, detail="Validator status required")
        
        # Verify signature
        commitment = f"zipcode:validation:{epoch_id}:{timestamp}"
        signature_valid = await verify_signature_with_timeout(commitment, signature, hotkey, NET_UID, BT_NETWORK)
        if not signature_valid:
            logger.warning(f"HISTORICAL EPOCH - Invalid signature: {hotkey}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Rate limiting for validators - 20 requests per hour
        rate_limit_key = f"zipcode_historical:{hotkey}:{time.strftime('%Y-%m-%d-%H')}"
        current_count = redis_client.get_counter(rate_limit_key)
        if current_count >= 20:
            raise HTTPException(status_code=429, detail="Rate limit exceeded: 20 requests per hour")
        redis_client.increment_counter(rate_limit_key, expire=3600)
        
        # Get historical epoch
        epoch = await epoch_manager.get_epoch_by_id(db, epoch_id)
        if not epoch:
            raise HTTPException(status_code=404, detail=f"Epoch {epoch_id} not found")
        
        # Build response (same format as current)
        zipcodes_data = []
        for assignment in epoch.assignments:
            zipcodes_data.append({
                "zipcode": assignment.zipcode,
                "expected_listings": assignment.expected_listings,
                "state": assignment.state,
                "city": assignment.city,
                "county": assignment.county,
                "market_tier": assignment.market_tier,
                "geographic_region": assignment.geographic_region
            })
        
        return {
            "success": True,
            "epoch_id": epoch.id,
            "epoch_start": epoch.start_time.isoformat(),
            "epoch_end": epoch.end_time.isoformat(),
            "nonce": epoch.nonce,
            "target_listings": epoch.target_listings,
            "tolerance_percent": epoch.tolerance_percent,
            "status": epoch.status,
            "zipcodes": zipcodes_data,
            "metadata": {
                "total_expected_listings": epoch.total_expected_listings,
                "zipcode_count": len(zipcodes_data),
                "algorithm_version": epoch.algorithm_version,
                "selection_seed": epoch.selection_seed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_historical_epoch: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/s3-access/validator-upload", tags=["Validator S3 Access"])
async def get_validator_s3_upload_access(request: ValidatorS3UploadRequest):
    """
    Provide S3 upload access for validators to store winning data.
    
    **Authentication**: Requires validator status + signature
    **Rate Limit**: 5 requests per hour per validator
    **Commitment Format**: `s3:validator:upload:{timestamp}`
    """
    try:
        hotkey, timestamp = request.hotkey, request.timestamp
        signature = request.signature
        epoch_id = request.epoch_id
        
        # Basic timestamp validation
        now = int(time.time())
        if abs(now - timestamp) > 300:
            raise HTTPException(status_code=400, detail="Invalid timestamp")
        
        # Verify validator status
        validator_status = await verify_validator_status_with_timeout(hotkey, NET_UID, BT_NETWORK)
        if not validator_status:
            logger.warning(f"VALIDATOR S3 ACCESS DENIED: {hotkey} - not a validator")
            raise HTTPException(status_code=403, detail="Validator status required")
        
        # Verify signature
        commitment = f"s3:validator:upload:{timestamp}"
        signature_valid = await verify_signature_with_timeout(commitment, signature, hotkey, NET_UID, BT_NETWORK)
        if not signature_valid:
            logger.warning(f"VALIDATOR S3 UPLOAD - Invalid signature: {hotkey}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Rate limiting - 5 requests per hour per validator
        rate_limit_key = f"validator_s3:{hotkey}:{time.strftime('%Y-%m-%d-%H')}"
        current_count = redis_client.get_counter(rate_limit_key)
        if current_count >= 5:
            raise HTTPException(status_code=429, detail="Rate limit exceeded: 5 S3 access requests per hour")
        redis_client.increment_counter(rate_limit_key, expire=3600)
        
        # Generate S3 credentials
        s3_response = await validator_s3_service.generate_temporary_credentials(
            validator_hotkey=hotkey,
            epoch_id=epoch_id,
            purpose=request.purpose
        )
        
        if not s3_response or not s3_response.get("success"):
            error_msg = s3_response.get("message", "Failed to generate S3 credentials") if s3_response else "S3 service unavailable"
            raise HTTPException(status_code=500, detail=error_msg)
        
        return s3_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_validator_s3_upload_access: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/zipcode-assignments/stats", tags=["System Health"])
async def get_zipcode_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get system statistics and health metrics.
    
    **Authentication**: None required (public endpoint)
    **Rate Limit**: 30 requests per minute globally
    """
    try:
        # Light rate limiting by IP
        client_ip = "global"  # Could get from request.client.host
        rate_limit_key = f"stats:{client_ip}:{time.strftime('%Y-%m-%d-%H-%M')}"
        current_count = redis_client.get_counter(rate_limit_key)
        if current_count >= 30:  # 30 requests per minute globally
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        redis_client.increment_counter(rate_limit_key, expire=60)
        
        # Get current epoch status
        epoch_status = await epoch_manager.get_epoch_status_summary(db)
        
        # Get zipcode statistics
        zipcode_stats = await zipcode_service.get_zipcode_statistics(db)
        
        # Get recent epochs
        recent_epochs = await epoch_manager.get_recent_epochs(db, limit=5)
        
        return {
            "success": True,
            "current_time": datetime.utcnow().isoformat(),
            "system_status": "operational",
            "epoch_status": epoch_status,
            "zipcode_statistics": zipcode_stats,
            "recent_performance": [
                {
                    "epoch_id": epoch.id,
                    "status": epoch.status,
                    "zipcodes_assigned": len(epoch.assignments),
                    "target_listings": epoch.target_listings,
                    "actual_expected": sum(a.expected_listings for a in epoch.assignments)
                }
                for epoch in recent_epochs
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_zipcode_statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/v1/zipcode-assignments/status", tags=["Zipcode Assignments"])
async def submit_completion_status(request: MinerStatusRequest, db: AsyncSession = Depends(get_db)):
    """
    Optional endpoint for miners to report completion status.
    
    **Authentication**: Requires miner signature + valid nonce
    **Rate Limit**: 10 status updates per hour per miner
    **Commitment Format**: `zipcode:status:{epoch_id}:{timestamp}`
    """
    try:
        hotkey, timestamp = request.hotkey, request.timestamp
        signature = request.signature
        epoch_id = request.epoch_id
        
        # Basic timestamp validation
        now = int(time.time())
        if abs(now - timestamp) > 300:
            raise HTTPException(status_code=400, detail="Invalid timestamp")
        
        # Verify signature
        commitment = f"zipcode:status:{epoch_id}:{timestamp}"
        signature_valid = await verify_signature_with_timeout(commitment, signature, hotkey, NET_UID, BT_NETWORK)
        if not signature_valid:
            logger.warning(f"MINER STATUS - Invalid signature: {hotkey}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Rate limiting - 10 status updates per hour per miner
        rate_limit_key = f"miner_status:{hotkey}:{time.strftime('%Y-%m-%d-%H')}"
        current_count = redis_client.get_counter(rate_limit_key)
        if current_count >= 10:
            raise HTTPException(status_code=429, detail="Rate limit exceeded: 10 status updates per hour")
        redis_client.increment_counter(rate_limit_key, expire=3600)
        
        # Verify epoch exists and nonce matches
        epoch = await epoch_manager.get_epoch_by_id(db, epoch_id)
        if not epoch:
            raise HTTPException(status_code=404, detail=f"Epoch {epoch_id} not found")
        
        if epoch.nonce != request.nonce:
            raise HTTPException(status_code=400, detail="Invalid nonce for epoch")
        
        # Store status update (optional - for monitoring)
        # This could be stored in MinerSubmission table if needed
        
        logger.info(f"Miner status update: {hotkey} - {epoch_id} - {request.status}")
        
        return {
            "success": True,
            "message": "Status update received",
            "epoch_id": epoch_id,
            "status": request.status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in submit_completion_status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# EXISTING S3 AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/get-folder-access", tags=["S3 Authentication"])
async def get_folder_access(request: MinerFolderAccessRequest):
    try:
        coldkey, hotkey = request.coldkey, request.hotkey
        timestamp = request.timestamp
        expiry = request.expiry or (timestamp + 86400)
        signature = request.signature

        # Folder path with data/ prefix
        folder_path = f"data/hotkey={hotkey}/"

        is_allowed, msg = check_rate_limit(hotkey, DAILY_LIMIT_PER_MINER)
        if not is_allowed:
            raise HTTPException(status_code=429, detail=msg)

        now = int(time.time())
        if now > expiry or now - timestamp > 300 or timestamp > now + 60:
            raise HTTPException(status_code=400, detail="Invalid timestamp")

        commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"

        # Use timeout-protected signature verification
        signature_valid = await verify_signature_with_timeout(commitment, signature, hotkey, NET_UID, BT_NETWORK)
        if not signature_valid:
            logger.warning(f"MINER SIGNATURE FAILED: {hotkey} (coldkey: {coldkey})")
            raise HTTPException(status_code=401, detail="Invalid signature")

        policy = generate_folder_upload_policy(S3_BUCKET, folder_path, expiry_hours=24)
        list_url = s3_client.generate_presigned_url(
            'list_objects_v2',
            Params={'Bucket': S3_BUCKET, 'Prefix': folder_path},
            ExpiresIn=60 * 60 * 3
        )

        return {
            'folder': folder_path,
            'url': policy['url'],
            'fields': policy['fields'],
            'expiry': datetime.fromtimestamp(expiry).isoformat(),
            'list_url': list_url,
            'structure_info': {
                'folder_structure': 'data/hotkey={hotkey_id}/job_id={job_id}/',
                'description': 'Upload files to job_id folders within your hotkey directory under data/ prefix'
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_folder_access: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-validator-access", tags=["S3 Authentication"])
async def get_validator_access(request: ValidatorAccessRequest):
    try:
        hotkey, timestamp = request.hotkey, request.timestamp
        signature = request.signature
        expiry = request.expiry or (timestamp + 86400)

        is_allowed, msg = check_rate_limit(hotkey, DAILY_LIMIT_PER_VALIDATOR)
        if not is_allowed:
            raise HTTPException(status_code=429, detail=msg)

        now = int(time.time())
        if now > expiry or now - timestamp > 300 or timestamp > now + 60:
            raise HTTPException(status_code=400, detail="Invalid timestamp")

        commitment = f"s3:validator:access:{timestamp}"

        # Use timeout-protected validator verification (2 minutes)
        validator_status = await verify_validator_status_with_timeout(hotkey, NET_UID, BT_NETWORK)
        if not validator_status:
            logger.warning(f"VALIDATOR ACCESS DENIED: {hotkey} - not a validator")
            raise HTTPException(status_code=401, detail="You are not validator")

        # Use timeout-protected signature verification
        signature_valid = await verify_signature_with_timeout(commitment, signature, hotkey, NET_UID, BT_NETWORK)
        if not signature_valid:
            logger.warning(f"VALIDATOR SIGNATURE FAILED: {hotkey}")
            raise HTTPException(status_code=401, detail="Invalid signature")

        return generate_validator_access_urls(hotkey, expiry_hours=24)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_validator_access: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-miner-specific-access")
async def get_miner_specific_access(request: ValidatorAccessRequest):
    """Get presigned URL for a specific miner's data with 2-minute timeout protection"""
    try:
        hotkey, timestamp = request.hotkey, request.timestamp
        signature = request.signature
        miner_hotkey = request.miner_hotkey
        expiry = request.expiry or (timestamp + 86400)

        if not miner_hotkey:
            raise HTTPException(status_code=400, detail="miner_hotkey is required")

        is_allowed, msg = check_rate_limit(hotkey, DAILY_LIMIT_PER_VALIDATOR)
        if not is_allowed:
            raise HTTPException(status_code=429, detail=msg)

        now = int(time.time())
        if now > expiry or now - timestamp > 300 or timestamp > now + 60:
            raise HTTPException(status_code=400, detail="Invalid timestamp")

        commitment = f"s3:validator:miner:{miner_hotkey}:{timestamp}"

        # Use timeout-protected validator verification (2 minutes)
        validator_status = await verify_validator_status_with_timeout(hotkey, NET_UID, BT_NETWORK)
        if not validator_status:
            logger.warning(f"VALIDATOR ACCESS DENIED: {hotkey} - not a validator (requested miner: {miner_hotkey})")
            raise HTTPException(status_code=401, detail="You are not validator")

        # Use timeout-protected signature verification
        signature_valid = await verify_signature_with_timeout(commitment, signature, hotkey, NET_UID, BT_NETWORK)
        if not signature_valid:
            logger.warning(f"VALIDATOR SIGNATURE FAILED: {hotkey} (requested miner: {miner_hotkey})")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Generate presigned URL with specific miner prefix
        miner_prefix = f"data/hotkey={miner_hotkey}/"

        try:
            presigned_url = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: s3_client.generate_presigned_url(
                        'list_objects_v2',
                        Params={
                            'Bucket': S3_BUCKET,
                            'Prefix': miner_prefix,
                            'MaxKeys': 10000
                        },
                        ExpiresIn=3 * 3600
                    )
                ),
                timeout=S3_OPERATION_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"S3 presigned URL generation timeout for {miner_hotkey}")
            monitor.count_request(timeout=True)
            raise HTTPException(status_code=504, detail="S3 operation timeout - try again")

        return {
            'bucket': S3_BUCKET,
            'region': S3_REGION,
            'miner_hotkey': miner_hotkey,
            'miner_url': presigned_url,
            'prefix': miner_prefix,
            'expiry': datetime.fromtimestamp(expiry).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_miner_specific_access: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/healthcheck", tags=["System Health"])
async def health_check():
    # Quick S3 test with timeout
    s3_ok = True
    s3_latency = 0
    start_time = time.time()

    try:
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: s3_client.head_bucket(Bucket=S3_BUCKET)
            ),
            timeout=5.0
        )
        s3_latency = time.time() - start_time
    except Exception as e:
        s3_ok = False
        logger.error(f"S3 health check failed: {str(e)}")

    # Quick Redis test
    redis_ok = True
    try:
        redis_client.set('ping', 'pong', expire=1)
        redis_ok = redis_client.get('ping') is not None
    except Exception as e:
        redis_ok = False
        logger.error(f"Redis health check failed: {str(e)}")

    # Database health check
    db_ok = await check_database_health()

    # Validator S3 service health check
    validator_s3_health = await validator_s3_service.get_service_health()

    stats = monitor.get_stats()

    # Check metagraph syncer status
    metagraph_ok = False
    metagraph_info = {}
    if metagraph_syncer is not None:
        try:
            metagraph = metagraph_syncer.get_metagraph(NET_UID)
            metagraph_ok = True
            metagraph_info = {
                'enabled': True,
                'netuid': NET_UID,
                'sync_interval': METAGRAPH_SYNC_INTERVAL,
                'hotkeys_count': len(metagraph.hotkeys) if metagraph else 0,
                'last_sync': 'recent' if metagraph else 'unknown'
            }
        except Exception as e:
            metagraph_info = {
                'enabled': True,
                'error': str(e)
            }
    else:
        metagraph_info = {
            'enabled': False,
            'reason': 'Initialization failed, using fallback methods'
        }

    # Overall system status
    critical_services_ok = s3_ok and redis_ok and metagraph_ok
    zipcode_services_ok = db_ok and validator_s3_health.get('validator_s3_service') != 'unhealthy'
    
    if critical_services_ok and zipcode_services_ok:
        overall_status = 'healthy'
    elif critical_services_ok:
        overall_status = 'degraded'  # Core S3 auth works, zipcode features may be limited
    else:
        overall_status = 'unhealthy'

    return {
        'status': overall_status,
        'timestamp': time.time(),
        'services': {
            's3_auth': {
                'status': 'ok' if s3_ok else 'error',
                'bucket': S3_BUCKET,
                'region': S3_REGION,
                'latency_ms': round(s3_latency * 1000, 2)
            },
            'redis': {
                'status': 'ok' if redis_ok else 'error'
            },
            'database': {
                'status': 'ok' if db_ok else 'error'
            },
            'validator_s3': validator_s3_health,
            'metagraph_syncer': metagraph_info
        },
        'features': {
            's3_authentication': s3_ok and redis_ok,
            'zipcode_assignments': db_ok,
            'validator_uploads': validator_s3_health.get('validator_s3_service') == 'healthy',
            'background_epoch_management': db_ok
        },
        'folder_structure': 'data/hotkey={hotkey_id}/job_id={job_id}/',
        'stats': stats,
        'timeouts': {
            'validator_verification': f"{VALIDATOR_VERIFICATION_TIMEOUT}s",
            'signature_verification': f"{SIGNATURE_VERIFICATION_TIMEOUT}s",
            's3_operations': f"{S3_OPERATION_TIMEOUT}s"
        }
    }


@app.get("/commitment-formats")
async def commitment_formats():
    return {
        'miner_format': "s3:data:access:{coldkey}:{hotkey}:{timestamp}",
        'validator_format': "s3:validator:access:{timestamp}",
        'miner_specific_format': "s3:validator:miner:{miner_hotkey}:{timestamp}",
        'example_miner': "s3:data:access:5F3...coldkey:5H2...hotkey:1682345678",
        'example_validator': "s3:validator:access:1682345678",
        'example_miner_specific': "s3:validator:miner:5F3...miner_hotkey:1682345678",
        'folder_structure': {
            'new_structure': 'data/hotkey={hotkey_id}/job_id={job_id}/',
            'description': 'Job-based folder structure with explicit labels under data/ prefix',
            'example_paths': [
                'data/hotkey=5F3...xyz/job_id=default_0/data_20250620_143052_150.parquet',
                'data/hotkey=5F3...xyz/job_id=crawler-7-h4rptebsja6qbdmocrt98/data_20250620_143055_67.parquet'
            ]
        },
        'instructions': "1. Generate timestamp\n2. Sign commitment\n3. Make API request\n4. Upload to job_id folders with explicit labels under data/ prefix",
        'timeout_protection': {
            'validator_verification': f"{VALIDATOR_VERIFICATION_TIMEOUT} seconds",
            'signature_verification': f"{SIGNATURE_VERIFICATION_TIMEOUT} seconds",
            'description': "All validation operations have timeout protection to prevent hanging"
        }
    }


@app.get("/structure-info")
async def structure_info():
    """Endpoint to get information about the new folder structure"""
    return {
        'folder_structure': 'data/hotkey={hotkey_id}/job_id={job_id}/',
        'changes': {
            'old_structure': 'hotkey={hotkey_id}/job_id={job_id}/',
            'new_structure': 'data/hotkey={hotkey_id}/job_id={job_id}/',
            'benefits': [
                'Explicit hotkey and job_id labeling',
                'Cleaner path structure with data/ prefix',
                'Better organization for miners and validators',
                '2-minute timeout protection for validator verification',
                'Comprehensive error handling and monitoring'
            ]
        },
        'example_paths': [
            'data/hotkey=5F3...xyz/job_id=default_0/data_20250620_143052_150.parquet',
            'data/hotkey=5F3...xyz/job_id=crawler-7-h4rptebsja6qbdmocrt98/data_20250620_143055_67.parquet'
        ],
        'upload_flow': [
            '1. Get job IDs from Gravity',
            '2. Request S3 credentials via API',
            '3. Upload files to data/hotkey={hotkey_id}/job_id={job_id}/ folders',
            '4. Each job gets its own folder with explicit labels under data/ prefix'
        ],
        'timeout_protection': {
            'validator_verification': f"{VALIDATOR_VERIFICATION_TIMEOUT} seconds (2 minutes)",
            'signature_verification': f"{SIGNATURE_VERIFICATION_TIMEOUT} seconds",
            's3_operations': f"{S3_OPERATION_TIMEOUT} seconds",
            'description': "All operations have timeout protection to prevent server hanging"
        }
    }


@app.get("/rate-limits")
async def get_rate_limits():
    """Get current rate limiting configuration"""
    today = time.strftime('%Y-%m-%d')
    
    # Get current usage for today
    global_key = f"GLOBAL:{today}"
    global_count = redis_client.get_counter(global_key)
    
    return {
        "rate_limits": {
            "daily_limit_per_miner": DAILY_LIMIT_PER_MINER,
            "daily_limit_per_validator": DAILY_LIMIT_PER_VALIDATOR,
            "total_daily_limit": TOTAL_DAILY_LIMIT
        },
        "current_usage": {
            "global_requests_today": global_count,
            "global_remaining": max(0, TOTAL_DAILY_LIMIT - global_count),
            "reset_time": "Midnight UTC daily"
        },
        "environment": {
            "network": BT_NETWORK,
            "subnet_id": NET_UID,
            "bucket": S3_BUCKET,
            "region": S3_REGION
        },
        "limits_explanation": {
            "miner_limit": f"Each miner can make {DAILY_LIMIT_PER_MINER} requests per day",
            "validator_limit": f"Each validator can make {DAILY_LIMIT_PER_VALIDATOR} requests per day", 
            "total_limit": f"All users combined can make {TOTAL_DAILY_LIMIT} requests per day",
            "reset_frequency": "Limits reset at midnight UTC every day"
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Run with optimized settings
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        reload=False,
        workers=1,
        loop="asyncio",
        timeout_keep_alive=180,  # 3 minutes to handle long operations
        timeout_graceful_shutdown=30
    )