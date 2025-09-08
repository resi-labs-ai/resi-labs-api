# S3 Storage API for Bittensor Subnet 46 - Resi Labs

This API provides S3 storage access for Bittensor Subnet 46, allowing miners to upload data directly to AWS S3 storage with blockchain-based authentication and folder-based access control. Forked and adapted from the SN13 Data Universe implementation.

**Subnet 46 Configuration**:
- **Network**: Bittensor Finney (NET_UID: 46)
- **Region**: US East (Ohio) - us-east-2
- **Buckets**: Development, Test, Staging, and Production environments

## Features

- **Folder-based access** using coldkey structure for miner isolation
- **Strong security** with policy-based restrictions and signature verification
- **Blockchain authentication** for miners and validators
- **Policy-based uploads** allowing efficient multi-file operations
- **Comprehensive validator access** to all miner data
- **Rate limiting** to prevent abuse
- **Compatible with HuggingFace** for smooth migration
- **FastAPI implementation** with automatic documentation
- **Docker support** for easy deployment

## Folder Structure

```
data/
├── x/  # X/Twitter data
│   ├── <miner_coldkey_1>/
│   │   ├── file1.parquet
│   │   ├── file2.parquet
│   │   └── ...
│   └── <miner_coldkey_2>/
│       ├── file1.parquet
│       └── ...
└── reddit/  # Reddit data
    ├── <miner_coldkey_1>/
    │   ├── file1.parquet
    │   └── ...
    └── <miner_coldkey_2>/
        └── ...
```

## Security Model

The security model ensures proper isolation between miners while giving validators complete access:

1. **Miner Isolation**: Each miner can only access their own folder (`data/<source>/<coldkey>/`)
2. **Policy Restrictions**: Upload policies restrict operations to specific folders
3. **Size Limits**: Files must be between 1KB and 5GB per upload
4. **Signature Verification**: All requests require valid blockchain signatures
5. **Time-Limited Access**: Access expires after 24 hours by default

## API Endpoints

### For Miners

- **`/get-folder-access`**: Get a policy for uploading multiple files to a folder
  - Creates a signed POST policy restricted to the miner's folder
  - Includes a listing URL for verifying uploads
  - Valid for 24 hours by default

### For Validators 

- **`/get-validator-access`**: Get comprehensive read access to all miner data
  - Provides organized URLs for global, source-level, and miner-specific access
  - Automatically discovers all miners in the system
  - Includes file listing and download capabilities

### Utility Endpoints

- **`/healthcheck`**: Check server status and configuration

## Setup Instructions

### Requirements

- Python 3.8+
- Required Python packages: `pip install -r requirements.txt`
- S3-compatible storage (AWS S3, MinIO, Cloudflare R2, etc.)
- AWS credentials with bucket access

### Configuration

The API supports multiple environments with different S3 buckets:

- **Development**: `1000-resilabs-caleb-dev-bittensor-sn46-datacollection`
- **Test**: `2000-resilabs-test-bittensor-sn46-datacollection` 
- **Staging**: `3000-resilabs-staging-bittensor-sn46-datacollection`
- **Production**: `4000-resilabs-prod-bittensor-sn46-datacollection`

Copy and configure environment files:
```bash
# For development
cp env.development.example .env.development
# Edit .env.development with your AWS credentials

# For production
cp env.production.example .env.production
# Edit .env.production with your AWS credentials
```

Required environment variables:
```bash
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET=your-bucket-name
S3_REGION=us-east-2
NET_UID=46
```

### Running the Server

#### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export S3_BUCKET=1000-resilabs-caleb-dev-bittensor-sn46-datacollection
export NET_UID=46

# Run the server
python -m uvicorn s3_storage_api.server:app --host 0.0.0.0 --port 8000 --reload
```

#### Docker Deployment
```bash
# Development
docker-compose up --build

# Production (with environment variables)
S3_BUCKET=4000-resilabs-prod-bittensor-sn46-datacollection \
AWS_ACCESS_KEY_ID=your-key \
AWS_SECRET_ACCESS_KEY=your-secret \
docker-compose up --build -d
```

#### AWS Deployment
See `DEPLOYMENT.md` for comprehensive AWS deployment instructions including ECS, Lambda, and other options.

## Testing

The repository includes several test utilities:

- **`cross_folder_test.py`**: Tests the security of folder isolation
- **`test_upload.py`**: Demonstrates miner upload workflows
- **`download_test.py`**: Tests validator download capabilities

Run tests with:

```bash
# Test folder security
python cross_folder_test.py

# Test upload capabilities
python test_upload.py

# Test validator capabilities
python download_test.py
```




## Migrating from HuggingFace

The recommended migration strategy:

1. **Dual Upload Phase**: Upload to both HuggingFace and S3
2. **Validator Update**: Update validators to check both systems
3. **S3-Only Phase**: Stop HuggingFace uploads once S3 is validated
4. **Historical Migration**: Move historical data as needed


## Security Best Practices

- Never expose AWS secret keys to clients
- Keep the authentication server behind a secure proxy
- Validate all inputs and enforce rate limits
- Monitor for unusual access patterns
- Regularly rotate AWS credentials
- Use the smallest set of S3 permissions needed