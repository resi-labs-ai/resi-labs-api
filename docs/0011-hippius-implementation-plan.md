# Hippius S3 Integration Implementation Plan
## Migrating from AWS S3 to Hippius Decentralized Storage

### Executive Summary

This document outlines a comprehensive plan to migrate from AWS S3 to Hippius decentralized storage for Bittensor Subnet 46. The migration will maintain the current security model while leveraging Hippius's sub-account system to provide isolated miner storage and validator read access through a private, secure file system.

### Current Architecture Analysis

Based on the existing codebase analysis, the current system provides:

- **Miner Isolation**: Each miner can only upload to `data/hotkey={hotkey}/` folders
- **Validator Access**: Validators can read all miner data via presigned URLs
- **Rate Limiting**: Redis-based rate limiting (20-500 requests/day per miner)
- **Blockchain Authentication**: Bittensor signature verification for all operations
- **Time-Limited Access**: 24-hour expiring presigned URLs

### Hippius Integration Strategy

## Phase 1: Infrastructure Setup

### 1.1 Master Account Configuration
```python
# Master Hippius account setup
HIPPIUS_MASTER_SEED = os.getenv('HIPPIUS_MASTER_SEED')  # Secure master account
HIPPIUS_ENDPOINT = "s3.hippius.com"
HIPPIUS_REGION = "decentralized"
```

### 1.2 Sub-Account Management System

Based on Hippius documentation, we'll use their sub-account system for secure isolation:

```python
class HippiusSubAccountManager:
    def __init__(self):
        self.master_client = self._create_master_client()
        self.redis_client = RedisClient()
    
    def create_miner_subaccount(self, miner_hotkey: str) -> dict:
        """Create secure sub-account for miner with upload-only permissions"""
        # Generate non-deterministic seed (CRITICAL for security)
        entropy = secrets.token_hex(32)
        timestamp = int(time.time())
        subaccount_seed = f"bt-miner-{miner_hotkey[:8]}-{timestamp}-{entropy}"
        
        # Create Hippius sub-account with Upload permissions only
        api_key = base64.b64encode(subaccount_seed.encode()).decode()
        
        # Store in secure database with encryption
        registration = {
            "miner_hotkey": miner_hotkey,
            "subaccount_seed": encrypt_data(subaccount_seed),  # Encrypt at rest
            "api_key": api_key,
            "bucket_name": f"bittensor-miner-{miner_hotkey}",
            "permissions": ["Upload"],
            "registered_at": timestamp,
            "status": "active"
        }
        
        return self._store_registration(registration)
    
    def create_validator_subaccount(self) -> dict:
        """Create read-only sub-account for validators"""
        # Single validator sub-account with read permissions to all buckets
        entropy = secrets.token_hex(32)
        validator_seed = f"bt-validator-global-{entropy}"
        api_key = base64.b64encode(validator_seed.encode()).decode()
        
        return {
            "subaccount_seed": validator_seed,
            "api_key": api_key,
            "permissions": ["Read"],
            "access_scope": "all_miner_buckets"
        }
```

### 1.3 Bucket Structure Design

Maintain current folder structure but with individual miner buckets:
```
Bucket: bittensor-miner-{hotkey}
├── data/
│   ├── job_id=001/
│   │   ├── file1.parquet
│   │   └── file2.parquet
│   └── job_id=002/
│       └── file3.parquet
└── .attribution/  # Cryptographic attribution files
    ├── job_id=001/
    └── job_id=002/
```

## Phase 2: Security Implementation

### 2.1 Cryptographic Attribution System

Implement the security model from your research document:

```python
class AttributionSystem:
    def create_upload_attribution(self, miner_hotkey: str, file_path: str, 
                                 file_data: bytes) -> dict:
        """Create cryptographic attribution for file uploads"""
        file_hash = hashlib.sha256(file_data).hexdigest()
        file_size = len(file_data)
        timestamp = int(time.time())
        nonce = secrets.token_hex(16)  # Prevent replay attacks
        
        # Create attribution message
        attribution_message = (
            f"{miner_hotkey}:{file_path}:{file_hash}:"
            f"{file_size}:{timestamp}:{nonce}"
        )
        
        # Sign with Bittensor hotkey (not sub-account)
        signature = self.sign_with_bittensor_key(attribution_message, miner_hotkey)
        
        return {
            "attribution_message": attribution_message,
            "signature": signature,
            "file_hash": file_hash,
            "file_size": file_size,
            "timestamp": timestamp,
            "nonce": nonce
        }
    
    def validate_file_attribution(self, bucket_name: str, object_key: str) -> bool:
        """Validate file was uploaded by authorized miner"""
        # Implementation follows research document validation logic
        # - Verify file integrity (hash matches)
        # - Check nonce uniqueness (prevent replay)
        # - Validate Bittensor signature
        # - Confirm miner registration timing
        pass
```

### 2.2 Access Control Matrix

| User Type | Permissions | Bucket Access | Implementation |
|-----------|-------------|---------------|----------------|
| **Miners** | Upload Only | Own bucket only | Individual sub-accounts with upload permissions |
| **Validators** | Read Only | All miner buckets | Special validator sub-account with global read access |
| **System** | Full Admin | All operations | Master account for management |

### 2.3 Nonce Management for Replay Prevention

```python
class NonceManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.nonce_expiry = 7 * 24 * 3600  # 7 days
    
    def is_nonce_used(self, miner_hotkey: str, nonce: str) -> bool:
        """Check if nonce has been used before"""
        key = f"nonce:{miner_hotkey}:{nonce}"
        return self.redis.get(key) is not None
    
    def mark_nonce_used(self, miner_hotkey: str, nonce: str):
        """Mark nonce as used with expiry"""
        key = f"nonce:{miner_hotkey}:{nonce}"
        self.redis.set(key, "1", expire=self.nonce_expiry)
```

## Phase 3: API Endpoint Migration

### 3.1 Miner Registration Endpoint

```python
@app.post("/register-miner")
async def register_miner(request: MinerRegistrationRequest):
    """Register miner and provision Hippius credentials"""
    try:
        # Verify miner controls their hotkey
        if not await verify_hotkey_control(request.miner_hotkey, request.proof):
            raise HTTPException(status_code=401, detail="Invalid hotkey proof")
        
        # Check if already registered
        existing = get_miner_registration(request.miner_hotkey)
        if existing and existing['status'] == 'active':
            raise HTTPException(status_code=409, detail="Miner already registered")
        
        # Create sub-account and bucket
        subaccount_manager = HippiusSubAccountManager()
        registration = subaccount_manager.create_miner_subaccount(request.miner_hotkey)
        
        # Create dedicated bucket
        hippius_client = create_hippius_client(registration['subaccount_seed'])
        hippius_client.make_bucket(registration['bucket_name'])
        
        return {
            "status": "registered",
            "bucket_name": registration['bucket_name'],
            "upload_endpoint": HIPPIUS_ENDPOINT,
            "credentials": {
                "access_key": registration['api_key'],
                "secret_key": registration['subaccount_seed']
            }
        }
    except Exception as e:
        logger.error(f"Miner registration failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")
```

### 3.2 Enhanced Upload Endpoint

```python
@app.post("/get-hippius-upload-access")
async def get_hippius_upload_access(request: MinerFolderAccessRequest):
    """Provide Hippius upload credentials with attribution"""
    try:
        # Existing validation logic...
        signature_valid = await verify_signature_with_timeout(
            commitment, signature, hotkey, NET_UID, BT_NETWORK
        )
        if not signature_valid:
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Get miner registration
        registration = get_miner_registration(hotkey)
        if not registration or registration['status'] != 'active':
            raise HTTPException(status_code=401, detail="Miner not registered")
        
        # Return Hippius credentials for direct upload
        return {
            "upload_method": "direct_hippius",
            "endpoint": HIPPIUS_ENDPOINT,
            "bucket_name": registration['bucket_name'],
            "credentials": {
                "access_key": registration['api_key'],
                "secret_key": decrypt_data(registration['subaccount_seed'])
            },
            "folder_prefix": f"data/",
            "attribution_required": True,
            "expiry": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Upload access error: {str(e)}")
        raise HTTPException(status_code=500, detail="Access denied")
```

### 3.3 Validator Access with Read-Only Credentials

```python
@app.post("/get-hippius-validator-access")
async def get_hippius_validator_access(request: ValidatorAccessRequest):
    """Provide read-only access to all miner data"""
    try:
        # Existing validator verification...
        validator_status = await verify_validator_status_with_timeout(
            hotkey, NET_UID, BT_NETWORK
        )
        if not validator_status:
            raise HTTPException(status_code=401, detail="Not a validator")
        
        # Get or create validator credentials
        validator_creds = get_or_create_validator_credentials()
        
        # List all active miner buckets
        active_miners = get_active_miners()
        bucket_list = [f"bittensor-miner-{miner['hotkey']}" for miner in active_miners]
        
        return {
            "access_method": "direct_hippius",
            "endpoint": HIPPIUS_ENDPOINT,
            "credentials": {
                "access_key": validator_creds['api_key'],
                "secret_key": validator_creds['subaccount_seed']
            },
            "accessible_buckets": bucket_list,
            "permissions": ["read", "list"],
            "expiry": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "usage_note": "Read-only access to all miner data"
        }
        
    except Exception as e:
        logger.error(f"Validator access error: {str(e)}")
        raise HTTPException(status_code=500, detail="Access denied")
```

## Phase 4: Miner Lifecycle Management

### 4.1 Deregistration System

```python
@app.post("/deregister-miner")
async def deregister_miner(request: MinerDeregistrationRequest):
    """Deactivate miner access and schedule cleanup"""
    try:
        # Verify authority to deregister (miner themselves or subnet owner)
        if not await verify_deregistration_authority(request):
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        registration = get_miner_registration(request.miner_hotkey)
        if not registration:
            raise HTTPException(status_code=404, detail="Miner not found")
        
        # Update status but keep record for validation
        registration['status'] = 'deregistered'
        registration['deregistered_at'] = int(time.time())
        registration['deregistration_reason'] = request.reason
        
        update_miner_registration(registration)
        
        # Schedule credential cleanup after validation period (30 days)
        schedule_credential_cleanup(request.miner_hotkey, delay_days=30)
        
        return {"status": "deregistered", "cleanup_scheduled": "30 days"}
        
    except Exception as e:
        logger.error(f"Deregistration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Deregistration failed")
```

### 4.2 Automated Cleanup System

```python
class CredentialCleanupService:
    def __init__(self):
        self.cleanup_delay = 30 * 24 * 3600  # 30 days
    
    async def cleanup_old_credentials(self):
        """Clean up credentials for deregistered miners after validation period"""
        cutoff = int(time.time()) - self.cleanup_delay
        old_registrations = get_deregistered_miners_before(cutoff)
        
        for registration in old_registrations:
            try:
                # Delete Hippius sub-account
                await self.delete_hippius_subaccount(registration['subaccount_id'])
                
                # Archive registration record
                archive_miner_registration(registration)
                
                logger.info(f"Cleaned up credentials for {registration['miner_hotkey']}")
                
            except Exception as e:
                logger.error(f"Cleanup failed for {registration['miner_hotkey']}: {e}")
```

## Phase 5: Migration Strategy

### 5.1 Parallel Operation Phase

1. **Dual System Operation**: Run both AWS S3 and Hippius systems in parallel
2. **Gradual Migration**: Migrate miners in batches to test stability
3. **Data Validation**: Ensure data integrity during transition
4. **Rollback Capability**: Maintain ability to revert to AWS S3 if needed

### 5.2 Migration Steps

```python
class MigrationManager:
    def __init__(self):
        self.aws_client = boto3.client('s3')
        self.hippius_client = None
    
    async def migrate_miner_data(self, miner_hotkey: str):
        """Migrate existing miner data from AWS S3 to Hippius"""
        try:
            # 1. Register miner in Hippius
            registration = await self.register_miner_hippius(miner_hotkey)
            
            # 2. List existing S3 data
            aws_objects = self.list_aws_objects(f"data/hotkey={miner_hotkey}/")
            
            # 3. Copy data to Hippius with attribution
            for obj in aws_objects:
                await self.copy_with_attribution(obj, registration)
            
            # 4. Validate migration
            if await self.validate_migration(miner_hotkey):
                logger.info(f"Migration completed for {miner_hotkey}")
                return True
            else:
                logger.error(f"Migration validation failed for {miner_hotkey}")
                return False
                
        except Exception as e:
            logger.error(f"Migration failed for {miner_hotkey}: {e}")
            return False
```

### 5.3 Testing Strategy

1. **Testnet First**: Complete migration on testnet (subnet 428)
2. **Small Batch**: Migrate 5-10 miners initially
3. **Performance Testing**: Validate upload/download speeds
4. **Security Testing**: Verify isolation and attribution
5. **Validator Testing**: Ensure read access works correctly

## Phase 6: Monitoring and Maintenance

### 6.1 Health Monitoring

```python
@app.get("/hippius-health")
async def hippius_health_check():
    """Monitor Hippius integration health"""
    try:
        # Test master account connectivity
        master_health = await test_master_account()
        
        # Test sub-account functionality
        subaccount_health = await test_subaccount_operations()
        
        # Check attribution system
        attribution_health = await test_attribution_validation()
        
        return {
            "status": "healthy" if all([master_health, subaccount_health, attribution_health]) else "degraded",
            "components": {
                "master_account": master_health,
                "subaccount_system": subaccount_health,
                "attribution_system": attribution_health
            },
            "active_miners": len(get_active_miners()),
            "total_buckets": await count_active_buckets()
        }
        
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 6.2 Performance Metrics

- **Upload Success Rate**: Track successful vs failed uploads
- **Attribution Validation Rate**: Monitor validation failures
- **Access Time**: Measure credential provisioning speed
- **Storage Costs**: Compare AWS S3 vs Hippius costs
- **Data Integrity**: Regular validation of stored files

## Phase 7: Security Considerations

### 7.1 Key Security Features

1. **Non-Deterministic Credentials**: Prevent credential prediction attacks
2. **Encrypted Storage**: All sub-account seeds encrypted at rest
3. **Nonce-Based Replay Prevention**: Prevent signature reuse
4. **Cryptographic Attribution**: Prove file authorship
5. **Time-Limited Access**: Automatic credential expiry
6. **Audit Logging**: Track all access and operations

### 7.2 Threat Mitigation

| Threat | Mitigation | Implementation |
|--------|------------|----------------|
| **Credential Theft** | Encrypted storage + rotation | Regular sub-account rotation |
| **Cross-Miner Access** | Bucket isolation | Individual miner buckets |
| **Replay Attacks** | Nonce tracking | Redis-based nonce storage |
| **File Tampering** | Attribution validation | SHA256 + signature verification |
| **Unauthorized Uploads** | Signature verification | Bittensor hotkey signatures |

## Phase 8: Cost Analysis

### 8.1 Current AWS S3 Costs vs Hippius

**AWS S3 (Current)**:
- Storage: ~$0.023/GB/month
- Requests: ~$0.0004/1000 requests
- Data transfer: ~$0.09/GB

**Hippius (Projected)**:
- Storage: Decentralized IPFS (cost structure TBD)
- Requests: Sub-account based (investigate pricing)
- Data transfer: IPFS network (potentially lower)

### 8.2 Implementation Costs

- Development time: ~2-3 months
- Testing phase: ~1 month
- Migration period: ~2-4 weeks
- Ongoing maintenance: Reduced (decentralized)

## Phase 9: Questions for Hippius Team

Based on your research and this plan, key questions to ask:

### 9.1 Technical Questions

1. **Read-Only Sub-Accounts**: Can we create sub-accounts with read-only access to multiple buckets owned by other sub-accounts?

2. **Bucket Policies**: Can we set bucket policies to allow cross-account read access for validators?

3. **Rate Limiting**: What are Hippius's rate limits and can they be customized for our use case?

4. **Credential Lifecycle**: What's the recommended approach for rotating/deleting sub-account credentials?

5. **Attribution Support**: Does Hippius support custom metadata for file attribution?

### 9.2 Business Questions

1. **Pricing Structure**: What are the costs for storage, requests, and sub-accounts?

2. **SLA/Uptime**: What availability guarantees does Hippius provide?

3. **Data Migration**: Do they provide tools for migrating from AWS S3?

4. **Support Level**: What technical support is available during migration?

## Phase 10: Implementation Timeline

### Month 1: Foundation
- Week 1-2: Set up Hippius master account and test environment
- Week 3-4: Implement sub-account management system

### Month 2: Core Features
- Week 1-2: Build attribution system and API endpoints
- Week 3-4: Implement miner registration and credential management

### Month 3: Testing & Migration
- Week 1-2: Testnet deployment and testing
- Week 3-4: Production migration planning and execution

### Month 4: Optimization
- Week 1-2: Performance tuning and monitoring
- Week 3-4: Documentation and team training

## Conclusion

This implementation plan provides a secure, scalable migration path from AWS S3 to Hippius while maintaining the current security model and improving decentralization. The key advantages include:

1. **True Decentralization**: Move away from centralized AWS infrastructure
2. **Enhanced Security**: Cryptographic attribution and isolated credentials
3. **Cost Optimization**: Potentially lower storage and transfer costs
4. **Improved Privacy**: Private file system without requiring public access
5. **Better Isolation**: Individual miner buckets with strict access controls

The plan addresses your specific requirements for miner upload capabilities, validator read access, and secure credential management while providing a clear path for implementation and testing.

Next steps should focus on engaging with the Hippius team to clarify technical capabilities and begin setting up the test environment for proof-of-concept development.
