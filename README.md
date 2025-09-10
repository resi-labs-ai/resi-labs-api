# S3 Storage API for Bittensor Subnet 46 - Resi Labs

A production-ready S3 authentication API for Bittensor Subnet 46, allowing miners to upload data and validators to access all data with blockchain-based authentication.

**🌐 Production API**: https://s3-auth-api.resilabs.ai
- **Health Check**: https://s3-auth-api.resilabs.ai/healthcheck  
- **API Documentation**: https://s3-auth-api.resilabs.ai/docs
- **Usage Guide**: https://s3-auth-api.resilabs.ai/commitment-formats

**🧪 Testnet API**: https://s3-auth-api-testnet.resilabs.ai
- **Health Check**: https://s3-auth-api-testnet.resilabs.ai/healthcheck  
- **API Documentation**: https://s3-auth-api-testnet.resilabs.ai/docs

**📋 Production Configuration**:
- **Network**: Bittensor Finney (NET_UID: 46)
- **Region**: US East (Ohio) - us-east-2
- **Production Bucket**: `4000-resilabs-prod-bittensor-sn46-datacollection`

**🧪 Testnet Configuration**:
- **Network**: Bittensor Testnet (NET_UID: 428)
- **Region**: US East (Ohio) - us-east-2
- **Testnet Bucket**: `2000-resilabs-test-bittensor-sn428-datacollection`

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

## 🚀 **Quick Start for Miners & Validators**

### **For Miners**
```python
import requests
import time
from bittensor import Keypair

# Your credentials
coldkey = "your-coldkey"
hotkey = "your-hotkey"  
keypair = Keypair.create_from_mnemonic("your-mnemonic")

# Create commitment and signature
timestamp = int(time.time())
commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
signature = keypair.sign(commitment).hex()

# Request folder access
response = requests.post("http://52.15.32.154:8000/get-folder-access", json={
    "coldkey": coldkey,
    "hotkey": hotkey, 
    "timestamp": timestamp,
    "signature": signature
})

# Use the returned URL and fields to upload to S3
```

### **For Validators**
```python
import requests
import time
from bittensor import Keypair

# Your validator credentials
hotkey = "your-validator-hotkey"
keypair = Keypair.create_from_mnemonic("your-mnemonic")

# Create commitment and signature  
timestamp = int(time.time())
commitment = f"s3:validator:access:{timestamp}"
signature = keypair.sign(commitment).hex()

# Request global access
response = requests.post("http://52.15.32.154:8000/get-validator-access", json={
    "hotkey": hotkey,
    "timestamp": timestamp, 
    "signature": signature
})

# Use the returned URLs to access all miner data
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

## 📚 **Documentation**

- **[FINAL_DEPLOYMENT_GUIDE.md](FINAL_DEPLOYMENT_GUIDE.md)**: Complete deployment process and architecture explanation
- **[API Documentation](http://52.15.32.154:8000/docs)**: Interactive API documentation  
- **[Commitment Formats](http://52.15.32.154:8000/commitment-formats)**: How to format requests and signatures

## 🏗️ **Architecture**

- **AWS ECS Fargate**: Serverless container hosting
- **AWS ECR**: Docker image registry  
- **AWS S3**: Data storage (4 environment buckets)
- **AWS Secrets Manager**: Secure credential storage
- **CloudWatch**: Logging and monitoring

## Testing

### 🚀 Quick Testing (Recommended)

**For Production (Subnet 46):**
- **[MINER_VALIDATOR_TESTING_GUIDE.md](MINER_VALIDATOR_TESTING_GUIDE.md)**: Complete testing guide for production API
- Quick test: `python api-test/test_mainnet_s3_auth.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY`

**For Testnet (Subnet 428):**
- **[TESTNET_MINER_VALIDATOR_TESTING_GUIDE.md](TESTNET_MINER_VALIDATOR_TESTING_GUIDE.md)**: Complete testing guide for testnet API
- Quick test: `python api-test/test_testnet_s3_auth.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY`

### 🔧 Development Testing

The repository includes several development test utilities:

- **`cross_folder_test.py`**: Tests the security of folder isolation
- **`test_upload.py`**: Demonstrates miner upload workflows
- **`download_test.py`**: Tests validator download capabilities

Run development tests with:

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