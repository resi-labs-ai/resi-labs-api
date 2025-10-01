# API Server Upgrade Action Plan - Zipcode Assignment System
**Repository**: 46-resi-labs-api  
**Target Deployment**: Digital Ocean  
**Timeline**: 4 weeks  

## Current System Analysis

### ✅ **Existing Capabilities**
- **FastAPI server** with S3 authentication for miners and validators
- **Bittensor integration** with hotkey signature verification and validator status checking
- **Rate limiting** with Redis (20 req/day miners, 10K req/day validators)
- **Timeout protection** for blockchain operations (2-minute validator verification)
- **S3 folder structure**: `data/hotkey={hotkey}/job_id={job_id}/`
- **Docker deployment** ready with production configuration
- **Health monitoring** with stats and error tracking

### 🔄 **Required Additions**
- **Zipcode assignment system** with 4-hour epochs
- **Nonce-based anti-gaming** mechanism
- **Validator S3 upload access** for storing winning data
- **Database layer** for epoch and zipcode management
- **Historical epoch data** for validation
- **Swagger/OpenAPI documentation**

## Implementation Plan

### **Phase 1: Database & Core Infrastructure (Week 1)**

#### **1.1 Database Setup**
```bash
# New dependencies to add to requirements.txt
sqlalchemy>=2.0.0
alembic>=1.12.0
asyncpg>=0.29.0  # PostgreSQL async driver
psycopg2-binary>=2.9.0  # PostgreSQL sync driver (backup)
```

#### **1.2 Database Schema Implementation**
Create new files:
- `s3_storage_api/models/` - SQLAlchemy models
- `s3_storage_api/database.py` - Database connection and session management
- `alembic/` - Database migrations
- `s3_storage_api/services/zipcode_service.py` - Zipcode selection logic

**Tables to create:**
```sql
-- Core tables from detailed spec
epochs (id, start_time, end_time, nonce, target_listings, status)
epoch_assignments (epoch_id, zipcode, expected_listings, state, city, market_tier)
zipcodes (zipcode, state, city, population, expected_listings, last_assigned)
validator_results (epoch_id, validator_hotkey, validation_timestamp, top_3_miners)
validation_audit (epoch_id, validator_hotkey, miner_hotkey, validation_result)
```

#### **1.3 Environment Configuration Updates**
Add to `.env` files:
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/zipcode_db

# Zipcode System Configuration
TARGET_LISTINGS=10000
TOLERANCE_PERCENT=10
EPOCH_DURATION_HOURS=4
COOLDOWN_HOURS=24
MIN_ZIPCODE_LISTINGS=200
MAX_ZIPCODE_LISTINGS=3000

# Security
ZIPCODE_SECRET_KEY=your_secret_key_for_nonce_generation

# S3 - Validator Results Bucket
S3_VALIDATOR_BUCKET=resi-validated-data
VALIDATOR_MIN_STAKE=1000
```

### **Phase 2: New API Endpoints (Week 2)**

#### **2.1 Zipcode Assignment Endpoints**
Add to `s3_storage_api/server.py`:

```python
# New endpoints to implement:
@app.get("/api/v1/zipcode-assignments/current")
async def get_current_zipcode_assignment()

@app.get("/api/v1/zipcode-assignments/epoch/{epoch_id}")  
async def get_historical_epoch()

@app.post("/api/v1/s3-access/validator-upload")
async def get_validator_s3_upload_access()

@app.get("/api/v1/zipcode-assignments/stats")
async def get_zipcode_statistics()

@app.post("/api/v1/zipcode-assignments/status")  # Optional
async def submit_completion_status()
```

#### **2.2 Epoch Management System**
Create `s3_storage_api/services/epoch_manager.py`:
- Automatic 4-hour epoch transitions (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
- Zipcode selection algorithm with population weighting
- Nonce generation: `hmac_sha256(SECRET_KEY, f"{epoch_id}:{start_time}:{zipcode_hash}")`
- Background task for epoch transitions

#### **2.3 Authentication Extensions**
Extend existing auth system in `s3_storage_api/utils/bt_utils.py`:
- New commitment formats:
  - Miners: `zipcode:assignment:current:{timestamp}`
  - Validators: `zipcode:validation:{epoch_id}:{timestamp}`
  - Validator S3: `s3:validator:upload:{timestamp}`

### **Phase 3: Validator S3 Upload System (Week 2-3)**

#### **3.1 S3 Bucket Configuration**
**Manual Setup Required:**
1. Create new S3 bucket: `resi-validated-data`
2. Configure IAM roles for validator upload access
3. Set bucket policies for time-limited credentials
4. Configure lifecycle rules for data retention

#### **3.2 Validator Upload Service**
Create `s3_storage_api/services/validator_s3_service.py`:
- Generate time-limited S3 credentials for validators
- Folder structure: `validators/{validator_hotkey}/epoch={epoch_id}/`
- Upload validation: metadata requirements, file size limits
- Audit logging for all validator uploads

### **Phase 4: Swagger Documentation & Testing (Week 3)**

#### **4.1 OpenAPI/Swagger Integration**
Update `s3_storage_api/server.py`:
```python
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Resi Labs API - Subnet 46",
        version="2.0.0",
        description="S3 Authentication and Zipcode Assignment API for Bittensor Subnet 46",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Swagger UI endpoint
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Resi Labs API Documentation",
    )
```

#### **4.2 Enhanced API Documentation**
- Request/response models with Pydantic
- Authentication examples for all endpoints  
- Rate limiting documentation
- Error response specifications
- Integration guides for miners/validators

### **Phase 5: Digital Ocean Deployment (Week 4)**

#### **5.1 Digital Ocean Compatibility Analysis** ✅
**No Issues Expected:**
- FastAPI/Python stack is platform-agnostic
- PostgreSQL available on Digital Ocean
- Redis available on Digital Ocean  
- S3 access works from any cloud provider (just network latency differences)
- Docker deployment works identically

**Advantages of Digital Ocean:**
- Simpler pricing and management
- Better performance monitoring tools
- Easier database backups
- More straightforward networking

#### **5.2 Infrastructure Setup**
**Manual Tasks Required:**
1. **Digital Ocean Droplet**: 4 CPU, 8GB RAM, Ubuntu 22.04
2. **Managed PostgreSQL**: 2GB RAM minimum
3. **Managed Redis**: 1GB RAM minimum  
4. **Load Balancer**: For high availability
5. **Spaces/CDN**: Optional for static assets

#### **5.3 Deployment Configuration**
Update `docker-compose.yml` for production:
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    
  # PostgreSQL will be managed service on Digital Ocean
```

## File Structure Changes

```
s3_storage_api/
├── server.py                    # ✏️ Extend with zipcode endpoints
├── config.py                    # ✏️ Add zipcode configuration  
├── database.py                  # ➕ New: Database connection
├── models/                      # ➕ New: SQLAlchemy models
│   ├── __init__.py
│   ├── epoch.py
│   ├── zipcode.py
│   └── validator_result.py
├── services/                    # ➕ New: Business logic
│   ├── __init__.py
│   ├── epoch_manager.py
│   ├── zipcode_service.py
│   └── validator_s3_service.py
├── utils/                       # ✏️ Extend existing
│   ├── bt_utils.py             # ✏️ Add new auth formats
│   └── ...existing files
└── tests/                       # ➕ New: Comprehensive tests
    ├── test_zipcode_endpoints.py
    ├── test_epoch_management.py
    └── test_validator_s3.py

alembic/                         # ➕ New: Database migrations
├── versions/
├── env.py
└── alembic.ini

requirements.txt                 # ✏️ Add database dependencies
docker-compose.yml              # ✏️ Update for production
.env.production                 # ✏️ Add zipcode configuration
```

## Testing Strategy

### **Unit Tests**
```bash
# Add to requirements.txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.25.0  # For FastAPI testing

# Test files to create:
api-test/test_zipcode_assignments.py
api-test/test_validator_s3_upload.py  
api-test/test_epoch_transitions.py
api-test/test_nonce_validation.py
```

### **Integration Tests**
- Full epoch creation and assignment flow
- Validator S3 upload with real credentials
- Database consistency across epoch transitions
- Rate limiting with Redis

### **Load Tests**
- 100+ concurrent miner requests for assignments
- Database performance under high load
- S3 credential generation performance

## Security Considerations

### **Enhanced Authentication**
- Extend existing hotkey signature system
- New commitment message formats for zipcode operations
- Validator stake verification for S3 upload access
- Time-limited S3 credentials (4-hour expiry)

### **Anti-Gaming Measures**
- Epoch-specific nonces prevent pre-scraping
- Timestamp validation (±5 minutes server time)
- Rate limiting prevents abuse
- Validator consensus tracking

## Monitoring & Alerting

### **New Metrics to Track**
```python
# Add to existing SimpleMonitor class
epoch_transitions_successful = 0
epoch_transitions_failed = 0
zipcode_assignments_generated = 0
validator_uploads_successful = 0
nonce_validation_failures = 0
```

### **Health Checks**
Extend `/healthcheck` endpoint:
- Database connection status
- Current epoch status  
- Zipcode assignment availability
- Validator S3 bucket access
- Redis cache performance

## Data Import Requirements

### **Zipcode Database Population**
**Manual Task - Week 1:**
1. **Source Data**: Zillow research data for listing counts
2. **Data Structure**: 
   ```python
   {
     "zipcode": "11211",
     "state": "NY", 
     "city": "Brooklyn",
     "population": 45000,
     "median_home_value": 850000,
     "expected_listings": 1200,
     "market_tier": "premium"
   }
   ```
3. **Import Script**: Create `scripts/import_zipcode_data.py`
4. **Validation**: Ensure data quality and completeness

## Configuration Management

### **Environment-Specific Settings**
```bash
# Development (.env.development)
TARGET_LISTINGS=5000
DATABASE_URL=postgresql://localhost:5432/zipcode_dev

# Production (.env.production)  
TARGET_LISTINGS=10000
DATABASE_URL=${MANAGED_POSTGRES_URL}
REDIS_URL=${MANAGED_REDIS_URL}
```

## Swagger Documentation Access

Once implemented, API documentation will be available at:
- **Swagger UI**: `https://your-api-domain.com/docs`
- **ReDoc**: `https://your-api-domain.com/redoc`  
- **OpenAPI JSON**: `https://your-api-domain.com/openapi.json`

## Success Criteria & Validation

### **Functional Requirements**
- [ ] Generate zipcode assignments every 4 hours automatically
- [ ] Target 10K ±10% listings per epoch (configurable)
- [ ] Prevent pre-scraping with epoch-specific nonces
- [ ] Authenticate all requests with bittensor signatures
- [ ] Store 7+ days of historical epoch data
- [ ] Handle 100+ concurrent miners and validators
- [ ] Provide S3 upload access for validators
- [ ] Complete Swagger documentation

### **Performance Requirements**
- [ ] < 200ms response time for current assignments
- [ ] 99.9% uptime with monitoring
- [ ] Zero missed epoch transitions
- [ ] Rate limiting prevents abuse
- [ ] Database queries optimized with proper indexing

### **Security Requirements** 
- [ ] All requests cryptographically signed and verified
- [ ] Only registered bittensor hotkeys can access
- [ ] Secure nonce generation prevents gaming
- [ ] Time-limited S3 credentials for validators
- [ ] Comprehensive audit logging

## Critical Questions & Decisions Needed

### **1. Zipcode Data Source**
- **Question**: Do you have access to Zillow research data with listing counts per zipcode?
- **Alternative**: Use public census data + Zillow API sampling for estimates
- **Impact**: Affects accuracy of TARGET_LISTINGS calculations

### **2. Geographic Focus**
- **Question**: Start with PA/NJ as mentioned, or nationwide from beginning?
- **Recommendation**: Start regional (PA/NJ/NY) for testing, expand gradually
- **Configuration**: `GEOGRAPHIC_REGIONS=["PA", "NJ", "NY"]` (configurable)

### **3. S3 Bucket Strategy**
- **Question**: Create new `resi-validated-data` bucket or use existing with new prefix?
- **Recommendation**: New bucket for cleaner separation and access control
- **Setup**: Manual S3 bucket creation with proper IAM policies

### **4. Database Hosting**
- **Question**: Digital Ocean Managed PostgreSQL vs self-hosted?
- **Recommendation**: Managed service for easier backups and maintenance
- **Cost**: ~$15-30/month for development, $50-100/month for production

### **5. Epoch Transition Reliability**
- **Question**: How critical is zero downtime during epoch transitions?
- **Implementation**: Background task with health monitoring and alerts
- **Fallback**: Manual epoch generation via admin endpoint if automation fails

### **6. Rate Limiting Adjustments**
- **Current**: 20 req/day miners, 10K req/day validators
- **Zipcode System**: Miners need 6 requests/day (every 4 hours), validators need historical access
- **Recommendation**: Separate rate limits for zipcode endpoints vs S3 access

## Next Steps & Dependencies

### **Week 1 Priorities**
1. **Database Setup**: Create PostgreSQL instance on Digital Ocean
2. **Data Import**: Source and import zipcode listing data  
3. **Core Models**: Implement SQLAlchemy models and migrations
4. **Basic Endpoints**: Implement current assignment endpoint

### **Blockers to Resolve**
1. **Zipcode Data**: Need source for expected listings per zipcode
2. **S3 Bucket**: Manual creation of validator results bucket
3. **Digital Ocean**: Account setup and managed services provisioning
4. **Validator Testing**: Need validator hotkeys for testing S3 upload

### **Risk Mitigation**
- **Database Migration**: Test thoroughly on development before production
- **Epoch Transitions**: Implement with extensive logging and monitoring
- **S3 Permissions**: Test validator upload access before deployment
- **Load Testing**: Validate performance before mainnet launch

---

## Summary

This plan upgrades the existing S3 authentication API to support the competitive zipcode mining system. The implementation leverages the existing FastAPI infrastructure while adding database-backed epoch management and validator S3 upload capabilities. Digital Ocean deployment will work seamlessly with the current Docker-based approach.

**Total Estimated Development Time**: 3-4 weeks
**Infrastructure Cost**: ~$100-200/month for production deployment
**Key Success Factor**: Reliable epoch transitions and validator consensus on assignments
