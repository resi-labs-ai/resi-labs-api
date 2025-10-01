#!/usr/bin/env python3
"""
Test the API server locally without requiring database setup
"""
import os
import sys
import time
import json
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_endpoints():
    """Test basic endpoints that don't require database"""
    import requests
    
    base_url = "http://localhost:8000"
    
    logger.info("Testing basic API endpoints...")
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/healthcheck", timeout=5)
        logger.info(f"Health check: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"Services status: {health_data.get('services', {})}")
        else:
            logger.error(f"Health check failed: {response.text}")
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
    
    # Test commitment formats
    try:
        response = requests.get(f"{base_url}/commitment-formats", timeout=5)
        logger.info(f"Commitment formats: {response.status_code}")
        if response.status_code == 200:
            formats = response.json()
            logger.info("Available commitment formats:")
            for key, value in formats.items():
                if isinstance(value, str):
                    logger.info(f"  {key}: {value}")
    except Exception as e:
        logger.error(f"Commitment formats error: {str(e)}")
    
    # Test Swagger docs
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        logger.info(f"Swagger docs: {response.status_code}")
        if response.status_code == 200:
            logger.info("✅ Swagger documentation is accessible")
        else:
            logger.error("❌ Swagger documentation failed")
    except Exception as e:
        logger.error(f"Swagger docs error: {str(e)}")
    
    # Test OpenAPI JSON
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=5)
        logger.info(f"OpenAPI JSON: {response.status_code}")
        if response.status_code == 200:
            openapi_data = response.json()
            logger.info(f"API title: {openapi_data.get('info', {}).get('title')}")
            logger.info(f"API version: {openapi_data.get('info', {}).get('version')}")
            
            # Count endpoints
            paths = openapi_data.get('paths', {})
            endpoint_count = len(paths)
            logger.info(f"Total endpoints: {endpoint_count}")
            
            # List new zipcode endpoints
            zipcode_endpoints = [path for path in paths.keys() if 'zipcode' in path]
            logger.info(f"Zipcode endpoints: {zipcode_endpoints}")
            
        else:
            logger.error("❌ OpenAPI JSON failed")
    except Exception as e:
        logger.error(f"OpenAPI JSON error: {str(e)}")

def test_zipcode_service():
    """Test zipcode service functionality without database"""
    logger.info("Testing ZipcodeService...")
    
    try:
        from s3_storage_api.services.zipcode_service import ZipcodeService
        
        service = ZipcodeService()
        
        # Test configuration loading
        logger.info(f"Target listings: {service.target_listings}")
        logger.info(f"State priorities: {service.state_priorities}")
        logger.info(f"Market tier weights: {service.market_tier_weights}")
        
        # Test seed generation
        epoch_id = "2024-09-30-16:00"
        seed = service.generate_epoch_seed(epoch_id)
        logger.info(f"Generated seed for {epoch_id}: {seed}")
        
        # Test nonce generation
        test_zipcodes = ["19102", "08540", "19103"]
        nonce = service.generate_epoch_nonce(epoch_id, test_zipcodes)
        logger.info(f"Generated nonce: {nonce}")
        
        logger.info("✅ ZipcodeService basic functionality works")
        
    except Exception as e:
        logger.error(f"❌ ZipcodeService error: {str(e)}")

def test_epoch_manager():
    """Test epoch manager functionality"""
    logger.info("Testing EpochManager...")
    
    try:
        from s3_storage_api.services.zipcode_service import ZipcodeService
        from s3_storage_api.services.epoch_manager import EpochManager
        
        zipcode_service = ZipcodeService()
        epoch_manager = EpochManager(zipcode_service)
        
        # Test epoch time calculations
        from datetime import datetime
        now = datetime.utcnow()
        
        current_start = epoch_manager.get_current_epoch_start(now)
        next_start = epoch_manager.get_next_epoch_start(now)
        
        logger.info(f"Current time: {now}")
        logger.info(f"Current epoch start: {current_start}")
        logger.info(f"Next epoch start: {next_start}")
        
        # Test epoch ID generation
        epoch_id = epoch_manager.generate_epoch_id(current_start)
        logger.info(f"Generated epoch ID: {epoch_id}")
        
        logger.info("✅ EpochManager basic functionality works")
        
    except Exception as e:
        logger.error(f"❌ EpochManager error: {str(e)}")

def test_validator_s3_service():
    """Test validator S3 service functionality"""
    logger.info("Testing ValidatorS3Service...")
    
    try:
        from s3_storage_api.services.validator_s3_service import ValidatorS3Service
        
        service = ValidatorS3Service()
        
        # Test configuration
        logger.info(f"Validator bucket: {service.validator_bucket}")
        logger.info(f"S3 region: {service.s3_region}")
        logger.info(f"Session duration: {service.session_duration} seconds")
        
        # Test folder path generation
        validator_hotkey = "5F3Ak7jgmP7QxYcpkm2bNrXqYw8sT9vL4nH6uR2eK1mZ8xC9"
        epoch_id = "2024-09-30-16:00"
        
        folder_path = service.generate_validator_folder_path(validator_hotkey, epoch_id)
        logger.info(f"Generated folder path: {folder_path}")
        
        # Test policy creation
        policy = service.create_validator_policy(validator_hotkey, epoch_id)
        logger.info(f"Generated IAM policy with {len(policy['Statement'])} statements")
        
        logger.info("✅ ValidatorS3Service basic functionality works")
        
    except Exception as e:
        logger.error(f"❌ ValidatorS3Service error: {str(e)}")

async def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("TESTING RESI LABS API - ZIPCODE ASSIGNMENT SYSTEM")
    logger.info("=" * 60)
    
    # Test services without database
    test_zipcode_service()
    print()
    
    test_epoch_manager()
    print()
    
    test_validator_s3_service()
    print()
    
    # Test API endpoints (requires server to be running)
    logger.info("Testing API endpoints (requires server running on localhost:8000)...")
    await test_basic_endpoints()
    
    logger.info("=" * 60)
    logger.info("TESTING COMPLETE")
    logger.info("=" * 60)
    logger.info("Next steps:")
    logger.info("1. Set up PostgreSQL database")
    logger.info("2. Run: python scripts/import_zipcode_data.py --sample 50 --init-db")
    logger.info("3. Start server: python -m uvicorn s3_storage_api.server:app --reload")
    logger.info("4. Visit: http://localhost:8000/docs")

if __name__ == "__main__":
    asyncio.run(main())
