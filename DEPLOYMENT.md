# Deployment Guide - Subnet 46 S3 API

This guide covers deploying the Subnet 46 S3 Authentication API to AWS.

## Overview

The API has been configured for your four S3 buckets:
- **Development**: `1000-resilabs-caleb-dev-bittensor-sn46-datacollection`
- **Test**: `2000-resilabs-test-bittensor-sn46-datacollection`
- **Staging**: `3000-resilabs-staging-bittensor-sn46-datacollection`
- **Production**: `4000-resilabs-prod-bittensor-sn46-datacollection`

All buckets are configured for `us-east-2` (Ohio) region.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **S3 Buckets** (already created)
3. **IAM User/Role** with S3 access
4. **Docker** (for containerized deployment)
5. **Python 3.12+** (for local development)

## Required AWS IAM Permissions

Your AWS credentials need the following S3 permissions for your buckets:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:ListBucketMultipartUploads",
                "s3:AbortMultipartUpload"
            ],
            "Resource": [
                "arn:aws:s3:::*resilabs*bittensor-sn46-datacollection",
                "arn:aws:s3:::*resilabs*bittensor-sn46-datacollection/*"
            ]
        }
    ]
}
```

## Environment Configuration

### 1. Create Environment File

Copy the appropriate environment template:

```bash
# For development
cp env.development.example .env.development

# For production  
cp env.production.example .env.production
```

### 2. Update AWS Credentials

Edit your environment file and add your AWS credentials:

```bash
# Required AWS credentials
AWS_ACCESS_KEY_ID=your-actual-access-key
AWS_SECRET_ACCESS_KEY=your-actual-secret-key
```

**Security Note**: Never commit actual credentials to version control!

## Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Development Environment
```bash
# Create .env.development with your credentials
cp env.development.example .env.development
# Edit .env.development with your actual AWS credentials

# Build and run
docker-compose up --build
```

#### Production Environment
```bash
# Create .env.production with your credentials
cp env.production.example .env.production
# Edit .env.production with your actual AWS credentials

# Deploy with production environment
S3_BUCKET=4000-resilabs-prod-bittensor-sn46-datacollection \
AWS_ACCESS_KEY_ID=your-key \
AWS_SECRET_ACCESS_KEY=your-secret \
docker-compose up --build -d
```

### Option 2: AWS ECS Deployment

1. **Build and Push to ECR**:
```bash
# Create ECR repository
aws ecr create-repository --repository-name subnet46-s3-api --region us-east-2

# Get login token
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-2.amazonaws.com

# Build and push
docker build -t subnet46-s3-api .
docker tag subnet46-s3-api:latest <account>.dkr.ecr.us-east-2.amazonaws.com/subnet46-s3-api:latest
docker push <account>.dkr.ecr.us-east-2.amazonaws.com/subnet46-s3-api:latest
```

2. **Create ECS Task Definition** with environment variables:
```json
{
    "family": "subnet46-s3-api",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "executionRoleArn": "arn:aws:iam::<account>:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "api",
            "image": "<account>.dkr.ecr.us-east-2.amazonaws.com/subnet46-s3-api:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "S3_BUCKET", "value": "4000-resilabs-prod-bittensor-sn46-datacollection"},
                {"name": "S3_REGION", "value": "us-east-2"},
                {"name": "NET_UID", "value": "46"},
                {"name": "BT_NETWORK", "value": "finney"}
            ],
            "secrets": [
                {"name": "AWS_ACCESS_KEY_ID", "valueFrom": "arn:aws:secretsmanager:us-east-2:<account>:secret:subnet46/aws-credentials:AWS_ACCESS_KEY_ID::"},
                {"name": "AWS_SECRET_ACCESS_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-2:<account>:secret:subnet46/aws-credentials:AWS_SECRET_ACCESS_KEY::"}
            ]
        }
    ]
}
```

### Option 3: AWS Lambda Deployment

For serverless deployment, you'll need to modify the application to work with AWS Lambda. Consider using Mangum for FastAPI-Lambda integration.

### Option 4: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export S3_BUCKET=1000-resilabs-caleb-dev-bittensor-sn46-datacollection
export S3_REGION=us-east-2
export NET_UID=46

# Run the server
python -m uvicorn s3_storage_api.server:app --host 0.0.0.0 --port 8000 --reload
```

## Testing the Deployment

### 1. Health Check
```bash
curl http://localhost:8000/healthcheck
```

### 2. API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

### 3. Test Miner Access
Use the test scripts in `s3_storage_api/tests/` directory.

## Security Considerations

1. **Use AWS Secrets Manager** for production credentials
2. **Enable VPC** for ECS deployments
3. **Use Application Load Balancer** with SSL/TLS
4. **Set up CloudWatch** logging and monitoring
5. **Enable S3 bucket versioning** and lifecycle policies
6. **Use IAM roles** instead of access keys when possible

## Monitoring and Logging

### CloudWatch Integration
```python
# Add to your environment variables
CLOUDWATCH_LOG_GROUP=/aws/ecs/subnet46-s3-api
CLOUDWATCH_LOG_STREAM=api-logs
```

### Metrics to Monitor
- Request count and latency
- Error rates
- S3 operation timeouts
- Validator verification times
- Redis connection status

## Environment-Specific Configurations

| Environment | Bucket | Rate Limits (Miner/Validator) | Use Case |
|-------------|--------|-------------------------------|----------|
| Development | 1000-resilabs-caleb-dev... | 20/10,000 | Local development, testing |
| Test | 2000-resilabs-test... | 100/50,000 | Automated testing, CI/CD |
| Staging | 3000-resilabs-staging... | 30/15,000 | Pre-production validation |
| Production | 4000-resilabs-prod... | 50/20,000 | Live subnet operations |

## Troubleshooting

### Common Issues

1. **S3 Access Denied**: Check IAM permissions and bucket policies
2. **Timeout Errors**: Adjust timeout configurations in environment variables
3. **Redis Connection**: Ensure Redis is accessible or configure external Redis
4. **Bittensor Network**: Verify network connectivity and subnet UID

### Logs Location
- Docker: `docker logs <container_id>`
- ECS: CloudWatch Logs
- Local: Console output

## Next Steps

1. **Set up monitoring** with CloudWatch or your preferred solution
2. **Configure alerts** for high error rates or timeouts
3. **Set up backup strategies** for Redis data
4. **Plan scaling** based on usage patterns
5. **Implement CI/CD pipeline** for automated deployments

## Support

For issues specific to Subnet 46, contact the Resi Labs team.
For Bittensor-related issues, refer to the official Bittensor documentation.
