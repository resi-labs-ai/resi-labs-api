# Infrastructure Setup Guide - Digital Ocean & S3

## Digital Ocean PostgreSQL Database Setup

### **Purpose**
The PostgreSQL database stores:
- **Epoch Management**: 4-hour cycles with zipcode assignments
- **Zipcode Master Data**: Listing counts, market tiers, selection history
- **Validator Results**: Scoring results, audit trails, consensus tracking
- **Historical Data**: 7+ days retention for validation processes

### **Step 1: Create Managed PostgreSQL Database**

1. **Login to Digital Ocean Console**
   - Go to https://cloud.digitalocean.com/
   - Navigate to "Databases" in the left sidebar

2. **Create Database Cluster**
   ```
   Database Engine: PostgreSQL 15
   Plan: Basic ($15/month for development, $50/month for production)
   Configuration:
   - Development: 1 GB RAM, 1 vCPU, 10 GB Disk
   - Production: 2 GB RAM, 1 vCPU, 25 GB Disk
   
   Datacenter Region: Choose closest to your users
   - New York (recommended for PA/NJ focus)
   - San Francisco (if West Coast users)
   
   Database Name: zipcode_assignments
   ```

3. **Configure Database Settings**
   ```
   Database Name: zipcode_assignments
   Username: api_user (will be auto-generated)
   Password: [Auto-generated secure password]
   
   Trusted Sources: 
   - Add your API server's IP address
   - Add your development machine IP for testing
   ```

4. **Get Connection Details**
   After creation, note these values for your `.env` file:
   ```bash
   # Example connection string format:
   DATABASE_URL=postgresql://api_user:password@db-postgresql-nyc1-12345-do-user-123456-0.b.db.ondigitalocean.com:25060/zipcode_assignments?sslmode=require
   
   # Individual components:
   DB_HOST=db-postgresql-nyc1-12345-do-user-123456-0.b.db.ondigitalocean.com
   DB_PORT=25060
   DB_NAME=zipcode_assignments
   DB_USER=api_user
   DB_PASSWORD=[your-generated-password]
   ```

### **Step 2: Configure Database Security**

1. **SSL Configuration** (Required)
   - Digital Ocean PostgreSQL requires SSL connections
   - Download the CA certificate from the database dashboard
   - Add to your connection string: `?sslmode=require`

2. **Firewall Rules**
   ```
   Trusted Sources to Add:
   - Your API server droplet IP
   - Your development machine IP (temporary)
   - Load balancer IP (if using one)
   ```

3. **Connection Pooling** (Recommended for production)
   ```
   Enable Connection Pooling: Yes
   Pool Mode: Transaction
   Pool Size: 25 (adjust based on API server load)
   ```

### **Step 3: Test Database Connection**

```bash
# Install PostgreSQL client tools
sudo apt-get update
sudo apt-get install postgresql-client

# Test connection
psql "postgresql://api_user:password@your-host:25060/zipcode_assignments?sslmode=require"

# Should connect successfully and show:
# zipcode_assignments=>
```

---

## S3 Bucket Setup for Validator Uploads

### **Purpose**
Create a separate S3 bucket for validators to upload winning data and validation results.

### **Step 1: Create S3 Bucket**

1. **Login to AWS Console**
   - Go to https://console.aws.amazon.com/s3/

2. **Create New Bucket**
   ```
   Bucket Name: resi-validated-data-[environment]
   Examples:
   - resi-validated-data-dev (development)
   - resi-validated-data-prod (production)
   
   Region: us-east-2 (Ohio) - same as existing miner bucket
   
   Object Ownership: ACLs disabled (recommended)
   Block Public Access: Keep all blocks enabled (private bucket)
   Bucket Versioning: Enable (for audit trail)
   Default Encryption: Enable with SSE-S3
   ```

### **Step 2: Create IAM Policy for Validator Access**

Create a new IAM policy: `ValidatorS3UploadPolicy`

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ValidatorUploadAccess",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::resi-validated-data-prod",
                "arn:aws:s3:::resi-validated-data-prod/validators/*"
            ],
            "Condition": {
                "StringLike": {
                    "s3:x-amz-metadata-epoch-id": "*",
                    "s3:x-amz-metadata-validator-hotkey": "*"
                }
            }
        },
        {
            "Sid": "ValidatorListAccess", 
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::resi-validated-data-prod",
            "Condition": {
                "StringLike": {
                    "s3:prefix": "validators/*"
                }
            }
        }
    ]
}
```

### **Step 3: Create IAM Role for API Server**

Create IAM role: `ApiServerValidatorS3Role`

1. **Trust Policy**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR-ACCOUNT-ID:user/api-server-user"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

2. **Attach Policies**:
   - `ValidatorS3UploadPolicy` (created above)
   - `AmazonS3ReadOnlyAccess` (for reading miner data)

### **Step 4: Configure Bucket Lifecycle Rules**

Set up automatic cleanup for old validation data:

```json
{
    "Rules": [
        {
            "ID": "ValidatorDataRetention",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "validators/"
            },
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "STANDARD_IA"
                },
                {
                    "Days": 90, 
                    "StorageClass": "GLACIER"
                }
            ],
            "Expiration": {
                "Days": 365
            }
        }
    ]
}
```

### **Step 5: Update API Server Environment Variables**

Add to your `.env.production` file:

```bash
# S3 Configuration
S3_MINER_BUCKET=1000-resilabs-caleb-dev-bittensor-sn46-datacollection
S3_VALIDATOR_BUCKET=resi-validated-data-prod
S3_REGION=us-east-2

# IAM Configuration for Validator S3 Access
VALIDATOR_S3_ROLE_ARN=arn:aws:iam::YOUR-ACCOUNT-ID:role/ApiServerValidatorS3Role
VALIDATOR_S3_SESSION_DURATION=14400  # 4 hours in seconds

# Validator Requirements
VALIDATOR_MIN_STAKE=1000  # Minimum stake required for S3 upload access
```

---

## Redis Setup (Optional - Digital Ocean Managed)

### **For Enhanced Performance** (Recommended for production)

1. **Create Managed Redis Cluster**
   ```
   Plan: Basic ($15/month)
   Configuration: 1 GB RAM
   Eviction Policy: allkeys-lru
   ```

2. **Update Environment Variables**
   ```bash
   REDIS_URL=rediss://default:password@redis-cluster-name.db.ondigitalocean.com:25061
   ```

---

## Environment Configuration Summary

### **Development Environment (.env.development)**
```bash
# Database
DATABASE_URL=postgresql://api_user:dev_password@localhost:5432/zipcode_dev

# S3
S3_MINER_BUCKET=1000-resilabs-caleb-dev-bittensor-sn46-datacollection
S3_VALIDATOR_BUCKET=resi-validated-data-dev
S3_REGION=us-east-2

# Zipcode System
TARGET_LISTINGS=5000
TOLERANCE_PERCENT=15
EPOCH_DURATION_HOURS=4
COOLDOWN_HOURS=24

# State Priorities (configurable)
STATE_PRIORITIES=PA:1,NJ:2,NY:3,DE:4,MD:5

# Security
ZIPCODE_SECRET_KEY=dev-secret-key-change-in-production
BT_NETWORK=test
NET_UID=46
```

### **Production Environment (.env.production)**
```bash
# Database
DATABASE_URL=postgresql://api_user:secure_password@db-host:25060/zipcode_assignments?sslmode=require

# S3
S3_MINER_BUCKET=1000-resilabs-caleb-dev-bittensor-sn46-datacollection
S3_VALIDATOR_BUCKET=resi-validated-data-prod
S3_REGION=us-east-2
VALIDATOR_S3_ROLE_ARN=arn:aws:iam::ACCOUNT:role/ApiServerValidatorS3Role

# Zipcode System
TARGET_LISTINGS=10000
TOLERANCE_PERCENT=10
EPOCH_DURATION_HOURS=4
COOLDOWN_HOURS=24

# State Priorities
STATE_PRIORITIES=PA:1,NJ:2,NY:3,DE:4,MD:5

# Security
ZIPCODE_SECRET_KEY=production-secret-key-32-chars-min
BT_NETWORK=finney
NET_UID=46
VALIDATOR_MIN_STAKE=1000

# Performance
REDIS_URL=rediss://default:password@redis-host:25061
```

---

## Security Checklist

### **Database Security**
- [ ] SSL connections enabled and enforced
- [ ] Firewall rules restrict access to known IPs
- [ ] Strong password generated and stored securely
- [ ] Connection pooling configured for production
- [ ] Regular backups enabled (automatic with managed service)

### **S3 Security**
- [ ] Bucket is private (no public access)
- [ ] IAM policies follow principle of least privilege
- [ ] Metadata requirements enforced for validator uploads
- [ ] Lifecycle rules configured for cost optimization
- [ ] Versioning enabled for audit trail

### **API Security**
- [ ] Secret keys are cryptographically secure (32+ characters)
- [ ] Environment variables properly configured
- [ ] Rate limiting configured appropriately
- [ ] Bittensor signature verification working

---

## Cost Estimates

### **Monthly Infrastructure Costs**

**Development Environment:**
- PostgreSQL (Basic): $15/month
- Redis (Optional): $15/month
- API Server Droplet: $12/month (2GB RAM)
- **Total: ~$42/month**

**Production Environment:**
- PostgreSQL (Standard): $50/month
- Redis: $15/month  
- API Server Droplet: $24/month (4GB RAM)
- Load Balancer: $12/month
- **Total: ~$101/month**

**S3 Storage Costs:**
- Validator data: ~$5-15/month (depending on volume)
- Existing miner data: (unchanged)

---

## Next Steps

1. **Create Digital Ocean Account** (if not already done)
2. **Set up PostgreSQL Database** following steps above
3. **Configure S3 Bucket** and IAM policies
4. **Test connections** from your development environment
5. **Update environment variables** in your API server
6. **Run database migrations** (we'll create these next)

Once infrastructure is ready, we can proceed with implementing the database models and API endpoints!
