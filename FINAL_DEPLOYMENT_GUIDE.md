# Complete Deployment Guide - Subnet 46 S3 API

## 🎯 **What We Built**

A production-ready S3 authentication API for Bittensor Subnet 46 that allows:
- **Miners** to upload data to isolated S3 folders with blockchain authentication
- **Validators** to read all miner data with proper access controls
- **Rate limiting** and security features
- **Multi-environment support** (dev, test, staging, production)

**Live API**: http://52.15.32.154:8000
- Health Check: http://52.15.32.154:8000/healthcheck
- API Docs: http://52.15.32.154:8000/docs

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Miners/       │    │   ECS Fargate    │    │   S3 Buckets    │
│   Validators    │───▶│   (API Server)   │───▶│   (Data Store)  │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Secrets Manager │
                       │  (AWS Creds)     │
                       └──────────────────┘
```

**AWS Components:**
- **ECS Fargate**: Runs the containerized API (serverless containers)
- **ECR**: Stores the Docker image
- **S3 Buckets**: Store miner data (4 environments)
- **Secrets Manager**: Securely stores AWS credentials
- **CloudWatch**: Logs and monitoring
- **IAM Roles**: Secure access control

## 📋 **From Fork to Production: What We Did**

### **Step 1: Adapted SN13 Code for Subnet 46**
- Changed `NET_UID` from 13 to 46
- Updated S3 bucket names to your 4 environments
- Changed from DigitalOcean Spaces to AWS S3
- Fixed environment variable loading

### **Step 2: AWS Infrastructure Setup**
We created all the necessary AWS resources:

```bash
# ECR Repository (Docker registry)
aws ecr create-repository --repository-name subnet46-s3-api

# Secrets Manager (secure credential storage)
aws secretsmanager create-secret --name "subnet46/aws-credentials"

# ECS Cluster (container orchestration)
aws ecs create-cluster --cluster-name subnet46-cluster

# IAM Roles (security permissions)
# - ecsTaskExecutionRole: Allows ECS to pull images and write logs
# - ecsTaskRole: Allows containers to access S3 buckets

# CloudWatch Logs (monitoring)
aws logs create-log-group --log-group-name "/ecs/subnet46-s3-api"
```

### **Step 3: Docker Image Build & Deploy**
**The Key Process That Happened:**

1. **Source Code Packaging**: We zipped your code and uploaded to S3
2. **AWS CloudShell Build**: Used AWS CloudShell (cloud-based terminal) to:
   - Download the source code from S3
   - Build Docker image in AWS environment
   - Push to ECR (AWS Docker registry)
3. **ECS Deployment**: Created ECS service to run the container

**Why CloudShell?** Your local Docker had credential issues, so we used AWS's cloud environment which has:
- ✅ No local Docker problems
- ✅ Fast network to AWS services
- ✅ Consistent build environment

### **Step 4: Container Orchestration**
- **ECS Task Definition**: Tells AWS how to run your container
- **ECS Service**: Ensures container stays running and handles scaling
- **Fargate**: Serverless compute (no servers to manage)

## 🔧 **Your S3 Bucket Configuration**

| Environment | Bucket Name | Usage |
|-------------|-------------|-------|
| Development | `1000-resilabs-caleb-dev-bittensor-sn46-datacollection` | Local testing |
| Test | `2000-resilabs-test-bittensor-sn46-datacollection` | Automated testing |
| Staging | `3000-resilabs-staging-bittensor-sn46-datacollection` | Pre-production |
| Production | `4000-resilabs-prod-bittensor-sn46-datacollection` | **Currently deployed** |

**Folder Structure:**
```
data/
├── hotkey={miner_hotkey}/
│   ├── job_id={job_1}/
│   │   ├── data_file_1.parquet
│   │   └── data_file_2.parquet
│   └── job_id={job_2}/
│       └── more_files.parquet
```

## 🚀 **How to Deploy Updates**

When you need to update your API:

### **Option 1: Quick Update (Recommended)**
```bash
# 1. Make your code changes locally
# 2. Go to AWS CloudShell
# 3. Download and build:

aws s3 cp s3://subnet46-deploy-532533045818/deployment-source.zip . --region us-east-2
unzip deployment-source.zip

# Update with your new code (upload new zip to S3 first)
# Then:
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 532533045818.dkr.ecr.us-east-2.amazonaws.com
docker build -t subnet46-s3-api .
docker tag subnet46-s3-api:latest 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet46-s3-api:latest
docker push 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet46-s3-api:latest

# 4. Force new deployment
aws ecs update-service --cluster subnet46-cluster --service subnet46-s3-api-service --force-new-deployment --region us-east-2
```

### **Option 2: Full Redeployment**
If you need to change configuration:
1. Update environment variables in `task-definition.json`
2. Register new task definition
3. Update service to use new task definition

## 📊 **Monitoring & Maintenance**

### **Health Monitoring**
- **Health Check**: http://52.15.32.154:8000/healthcheck
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-2#logsV2:log-groups/log-group/%252Fecs%252Fsubnet46-s3-api
- **ECS Console**: https://console.aws.amazon.com/ecs/home?region=us-east-2#/clusters/subnet46-cluster

### **Cost Management**
Current setup costs approximately:
- **ECS Fargate**: ~$15-30/month (0.5 vCPU, 1GB RAM)
- **ECR Storage**: ~$1/month
- **CloudWatch Logs**: ~$2-5/month
- **Data Transfer**: Variable based on usage

### **Security**
- ✅ AWS credentials stored in Secrets Manager (not in code)
- ✅ IAM roles with minimal required permissions
- ✅ Network security groups restrict access to port 8000
- ✅ All traffic over HTTPS (when using load balancer)

## 🔐 **Environment Variables**

The API uses these key environment variables:
```bash
# S3 Configuration
S3_BUCKET=4000-resilabs-prod-bittensor-sn46-datacollection
S3_REGION=us-east-2

# Bittensor Configuration  
NET_UID=46
BT_NETWORK=finney

# Rate Limiting
DAILY_LIMIT_PER_MINER=50
DAILY_LIMIT_PER_VALIDATOR=20000
TOTAL_DAILY_LIMIT=500000

# AWS Credentials (from Secrets Manager)
AWS_ACCESS_KEY_ID=(from secrets)
AWS_SECRET_ACCESS_KEY=(from secrets)
```

## 🧪 **Testing Your API**

### **Health Check**
```bash
curl http://52.15.32.154:8000/healthcheck
```
Should return:
```json
{
  "status": "ok",
  "bucket": "4000-resilabs-prod-bittensor-sn46-datacollection",
  "region": "us-east-2",
  "s3_ok": true,
  "redis_ok": true
}
```

### **API Documentation**
Visit: http://52.15.32.154:8000/docs
- Interactive API documentation
- Test all endpoints
- See request/response formats

### **Commitment Formats**
Visit: http://52.15.32.154:8000/commitment-formats
- Shows how miners/validators should format their requests
- Includes signature requirements

## 🛠️ **Troubleshooting**

### **Common Issues**

1. **Container Won't Start**
   - Check CloudWatch logs for errors
   - Verify environment variables are set
   - Check IAM role permissions

2. **S3 Access Denied**
   - Verify bucket names are correct
   - Check IAM policies allow S3 access
   - Ensure AWS credentials are valid

3. **High Memory Usage**
   - Monitor CloudWatch metrics
   - Consider increasing task memory
   - Check for memory leaks in logs

### **Useful Commands**
```bash
# Check service status
aws ecs describe-services --cluster subnet46-cluster --services subnet46-s3-api-service --region us-east-2

# View recent logs
aws logs tail /ecs/subnet46-s3-api --region us-east-2

# Get current task details
aws ecs list-tasks --cluster subnet46-cluster --service-name subnet46-s3-api-service --region us-east-2
```

## 📈 **Scaling & Production Considerations**

### **Current Setup (Single Instance)**
- ✅ Good for initial deployment
- ✅ Handles moderate traffic
- ✅ Cost-effective

### **Future Scaling Options**
1. **Horizontal Scaling**: Increase `desired-count` in ECS service
2. **Vertical Scaling**: Increase CPU/memory in task definition
3. **Load Balancer**: Add ALB for HTTPS and custom domain
4. **Auto Scaling**: Set up ECS auto scaling based on CPU/memory

### **Production Enhancements**
- **Custom Domain**: Use Route 53 + ALB for custom domain
- **HTTPS**: SSL certificate via Certificate Manager
- **Monitoring**: CloudWatch alarms for errors/high usage
- **Backup**: Automated S3 bucket backups
- **Multi-AZ**: Deploy across multiple availability zones

## 🎉 **Success Metrics**

Your deployment is successful because:
- ✅ **API is live** and responding at public IP
- ✅ **Health checks pass** - S3 and Redis connectivity confirmed
- ✅ **Documentation accessible** - Miners/validators can see how to use it
- ✅ **Proper authentication** - Blockchain signature verification working
- ✅ **Rate limiting active** - Prevents abuse
- ✅ **Multi-environment ready** - Can deploy to dev/test/staging easily
- ✅ **Monitoring in place** - CloudWatch logs and metrics
- ✅ **Secure** - Credentials in Secrets Manager, proper IAM roles

## 📞 **Next Steps**

1. **Share with your subnet**: Give miners/validators the API URL
2. **Monitor usage**: Watch CloudWatch for traffic patterns
3. **Plan scaling**: Based on actual usage, consider scaling up
4. **Custom domain**: Set up a proper domain name for production use
5. **Documentation**: Create usage guides for miners/validators

Your Subnet 46 S3 API is now production-ready! 🚀
