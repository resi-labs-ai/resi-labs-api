# 0002 - Testnet Deployment Guide (Subnet 428)

**Date**: September 10, 2025  
**Target Environment**: Testnet  
**Subnet**: 428  
**Network**: test  
**Domain**: s3-auth-api-testnet.resilabs.ai

## 📋 **Overview**

Complete guide to deploy the Subnet 46 S3 API on Bittensor testnet (subnet 428) with identical AWS infrastructure but separate resources. This creates a parallel testing environment without affecting production.

## 🎯 **Key Differences from Production**

| Component | Production (Subnet 46) | Testnet (Subnet 428) |
|-----------|------------------------|----------------------|
| **Subnet ID** | 46 | 428 |
| **Network** | finney | test |
| **Domain** | s3-auth-api.resilabs.ai | s3-auth-api-testnet.resilabs.ai |
| **S3 Bucket** | 4000-resilabs-prod-bittensor-sn46-datacollection | 2000-resilabs-test-bittensor-sn428-datacollection |
| **ECS Cluster** | subnet46-cluster | subnet428-testnet-cluster |
| **ALB Name** | subnet46-alb | subnet428-testnet-alb |
| **ECR Repository** | subnet46-s3-api | subnet428-testnet-s3-api |

## 🏗️ **Infrastructure to Create**

### **AWS Resources Needed**
- **ECS Fargate Cluster**: `subnet428-testnet-cluster`
- **ECS Service**: `subnet428-testnet-s3-api-service`
- **ECR Repository**: `subnet428-testnet-s3-api`
- **Application Load Balancer**: `subnet428-testnet-alb`
- **Target Group**: `subnet428-testnet-tg`
- **Security Groups**: `subnet428-testnet-alb-sg`, `subnet428-testnet-api-sg`
- **SSL Certificate**: ACM certificate for `s3-auth-api-testnet.resilabs.ai`
- **Secrets Manager**: `subnet428-testnet/aws-credentials`
- **CloudWatch Log Group**: `/ecs/subnet428-testnet-s3-api`

### **S3 Bucket Configuration**
- **Bucket Name**: `2000-resilabs-test-bittensor-sn428-datacollection`
- **Region**: `us-east-2`
- **Permissions**: Same IAM policies as production
- **CORS Configuration**: Same as production

## 🚀 **Complete Deployment Process**

### **Phase 1: Prerequisites Setup**

#### **1.1 AWS CLI Configuration**
```bash
# Ensure AWS CLI is configured
aws configure list
aws sts get-caller-identity
```

#### **1.2 Create S3 Bucket (if not exists)**
```bash
# Create testnet S3 bucket
aws s3 mb s3://2000-resilabs-test-bittensor-sn428-datacollection --region us-east-2

# Configure CORS (create cors-config.json first)
aws s3api put-bucket-cors --bucket 2000-resilabs-test-bittensor-sn428-datacollection --cors-configuration file://cors-config.json
```
(This threw an error: (venv) MacBook-Pro-85:46-resi-labs-api calebgates$ aws s3api put-bucket-cors --bucket 2000-resilabs-test-bittensor-sn428-datacollection --cors-configuration file://cors-config.json

Error parsing parameter '--cors-configuration': Unable to load paramfile file://cors-config.json: [Errno 2] No such file or directory: 'cors-config.json')

#### **1.3 Verify Domain Access**
- Ensure you have access to GoDaddy DNS for `resilabs.ai`
- Verify Route 53 hosted zone exists for `resilabs.ai`

### **Phase 2: Code Configuration**

#### **2.1 Create Testnet Environment File**
Create `.env.testnet`:
```bash
# Bittensor Network Configuration
BT_NETWORK=test
NET_UID=428

# AWS S3 Configuration
S3_BUCKET=2000-resilabs-test-bittensor-sn428-datacollection
S3_REGION=us-east-2
AWS_ACCESS_KEY_ID=your-testnet-access-key
AWS_SECRET_ACCESS_KEY=your-testnet-secret-key

# API Configuration
PORT=8000
DAILY_LIMIT_PER_MINER=50
DAILY_LIMIT_PER_VALIDATOR=20000
TOTAL_DAILY_LIMIT=500000

# Redis Configuration (if using)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
```

#### **2.2 Update Docker Compose for Testnet**
Create `docker-compose.testnet.yml`:
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.testnet
    environment:
      - PORT=8000
    volumes:
      - ./s3_storage_api:/app/s3_storage_api
    restart: unless-stopped
```

### **Phase 3: AWS Infrastructure Setup**

#### **3.1 Create ECR Repository**
```bash
# Create testnet ECR repository
aws ecr create-repository \
    --repository-name subnet428-testnet-s3-api \
    --region us-east-2 \
    --profile resilabs-admin

# Get login token and login to ECR
aws ecr get-login-password --region us-east-2 --profile resilabs-admin | docker login --username AWS --password-stdin 532533045818.dkr.ecr.us-east-2.amazonaws.com
```

#### **3.2 Build and Push Docker Image**
```bash
# Make sure docker desktop is running
(Start docker desktop)

# Build image for testnet
docker build -t subnet428-testnet-s3-api:latest .

# Tag for ECR
docker tag subnet428-testnet-s3-api:latest 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet428-testnet-s3-api:latest

# Push to ECR
docker push 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet428-testnet-s3-api:latest
```

#### **3.3 Create Secrets Manager Secret**
```bash
# Create testnet secrets (use admin profile if prod-deployment-user lacks permissions)
aws secretsmanager create-secret \
    --name "subnet428-testnet/aws-credentials" \
    --description "AWS credentials for Subnet 428 testnet S3 API" \
    --secret-string '{"AWS_ACCESS_KEY_ID":"your-key","AWS_SECRET_ACCESS_KEY":"your-secret"}' \
    --region us-east-2 \
    --profile resilabs-admin

# ✅ COMPLETED - Secret ARN: arn:aws:secretsmanager:us-east-2:532533045818:secret:subnet428-testnet/aws-credentials-vtnEGl
```

#### **3.4 Create ECS Cluster**
```bash
# Create testnet ECS cluster
aws ecs create-cluster \
    --cluster-name subnet428-testnet-cluster \
    --region us-east-2 \
    --profile resilabs-admin

# ✅ COMPLETED - Cluster ARN: arn:aws:ecs:us-east-2:532533045818:cluster/subnet428-testnet-cluster
```

#### **3.5 Create CloudWatch Log Group**
```bash
# Create log group for testnet
aws logs create-log-group \
    --log-group-name /ecs/subnet428-testnet-s3-api \
    --region us-east-2 \
    --profile resilabs-admin
```

### **Phase 4: SSL Certificate Setup**

#### **4.1 Request ACM Certificate**
```bash
# Request SSL certificate for testnet domain
aws acm request-certificate \
    --domain-name s3-auth-api-testnet.resilabs.ai \
    --validation-method DNS \
    --region us-east-2 \
    --profile resilabs-admin
```

#### **4.2 Get Certificate Validation Records**
```bash
# Get certificate ARN from previous command output
CERTIFICATE_ARN="arn:aws:acm:us-east-2:532533045818:certificate/your-cert-arn"

# Get validation records
aws acm describe-certificate \
    --certificate-arn $CERTIFICATE_ARN \
    --region us-east-2 \
    --profile resilabs-admin \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord'
```

#### **4.3 Add Validation Record to Route 53**
```bash
# Get hosted zone ID for resilabs.ai
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='resilabs.ai.'].Id" --output text --profile resilabs-admin | cut -d'/' -f3)

# Create validation record (using actual values from step 4.2)
aws route53 change-resource-record-sets \
    --hosted-zone-id Z0114515IKPREXJRDQ2C \
    --profile resilabs-admin \
    --change-batch '{
        "Changes": [{
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "_b48eacf7025e6af43d465718b2a851df.s3-auth-api-testnet.resilabs.ai.",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "_1e07b1c267e2ec6bb0c14171d39a39a3.xlfgrmvvlj.acm-validations.aws."}]
            }
        }]
    }'

# ✅ COMPLETED - Validation record added to Route 53, Change ID: C03620051Y9U9UE2BCUBB
```

#### **4.4 Wait for Certificate Validation**
```bash
# Check certificate status
aws acm describe-certificate \
    --certificate-arn $CERTIFICATE_ARN \
    --region us-east-2 \
    --profile resilabs-admin \
    --query 'Certificate.Status' \
    --output text
```

### **Phase 5: ECS Task Definition and Service**

#### **5.1 Create Task Definition**
Create `testnet-task-definition.json`:
```json
{
    "family": "subnet428-testnet-s3-api",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::532533045818:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::532533045818:role/ecsTaskRole",
    "containerDefinitions": [
        {
            "name": "subnet428-testnet-api",
            "image": "532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet428-testnet-s3-api:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "environment": [
                {"name": "PORT", "value": "8000"},
                {"name": "S3_BUCKET", "value": "2000-resilabs-test-bittensor-sn428-datacollection"},
                {"name": "S3_REGION", "value": "us-east-2"},
                {"name": "NET_UID", "value": "428"},
                {"name": "BT_NETWORK", "value": "test"},
                {"name": "DAILY_LIMIT_PER_MINER", "value": "50"},
                {"name": "DAILY_LIMIT_PER_VALIDATOR", "value": "20000"},
                {"name": "TOTAL_DAILY_LIMIT", "value": "500000"}
            ],
            "secrets": [
                {
                    "name": "AWS_ACCESS_KEY_ID",
                    "valueFrom": "arn:aws:secretsmanager:us-east-2:532533045818:secret:subnet428-testnet/aws-credentials:AWS_ACCESS_KEY_ID::"
                },
                {
                    "name": "AWS_SECRET_ACCESS_KEY",
                    "valueFrom": "arn:aws:secretsmanager:us-east-2:532533045818:secret:subnet428-testnet/aws-credentials:AWS_SECRET_ACCESS_KEY::"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/subnet428-testnet-s3-api",
                    "awslogs-region": "us-east-2",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
```

#### **5.2 Register Task Definition**
```bash
aws ecs register-task-definition \
    --cli-input-json file://testnet-task-definition.json \
    --region us-east-2 \
    --profile resilabs-admin
```

#### **5.3 Create ECS Service (Initial)**
```bash
# Get default VPC and subnets
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --profile resilabs-admin)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[].SubnetId' --output text --profile resilabs-admin | tr '\t' ',')

# Create initial ECS service
aws ecs create-service \
    --cluster subnet428-testnet-cluster \
    --service-name subnet428-testnet-s3-api-service \
    --task-definition subnet428-testnet-s3-api \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[],assignPublicIp=ENABLED}" \
    --region us-east-2 \
    --profile resilabs-admin
```

### **Phase 6: Load Balancer Setup**

#### **6.1 Create Security Groups**
```bash
# Create ALB security group
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name subnet428-testnet-alb-sg \
    --description "Security group for Subnet 428 testnet ALB" \
    --vpc-id $VPC_ID \
    --profile resilabs-admin \
    --query 'GroupId' --output text)

# Allow HTTP and HTTPS traffic to ALB
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --profile resilabs-admin

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --profile resilabs-admin

# Create ECS security group
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name subnet428-testnet-api-sg \
    --description "Security group for Subnet 428 testnet ECS tasks" \
    --vpc-id $VPC_ID \
    --profile resilabs-admin \
    --query 'GroupId' --output text)

# Allow traffic from ALB to ECS on port 8000
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG_ID \
    --profile resilabs-admin
```

#### **6.2 Create Application Load Balancer**
```bash
# Get subnet IDs for ALB (need at least 2 in different AZs)
SUBNET_1=$(echo $SUBNET_IDS | cut -d',' -f1)
SUBNET_2=$(echo $SUBNET_IDS | cut -d',' -f2)

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name subnet428-testnet-alb \
    --subnets $SUBNET_1 $SUBNET_2 \
    --security-groups $ALB_SG_ID \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --profile resilabs-admin \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --profile resilabs-admin \
    --query 'LoadBalancers[0].DNSName' --output text)

echo "ALB DNS Name: $ALB_DNS"
```

#### **6.3 Create Target Group**
```bash
# Create target group
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name subnet428-testnet-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /healthcheck \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --profile resilabs-admin \
    --query 'TargetGroups[0].TargetGroupArn' --output text)

echo "Target Group ARN: $TARGET_GROUP_ARN"
```

#### **6.4 Create HTTPS Listener**
```bash
# Create HTTPS listener with SSL certificate
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=$CERTIFICATE_ARN \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
```

### **Phase 7: Connect ECS Service to Load Balancer**

#### **7.1 Update ECS Service**
```bash
# Update ECS service to use load balancer
aws ecs update-service \
    --cluster subnet428-testnet-cluster \
    --service subnet428-testnet-s3-api-service \
    --load-balancers targetGroupArn=$TARGET_GROUP_ARN,containerName=subnet428-testnet-api,containerPort=8000 \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
    --region us-east-2 \
    --profile resilabs-admin
```

### **Phase 8: DNS Configuration**

#### **8.1 Add CNAME Record in GoDaddy**
**Manual Step - GoDaddy DNS Management:**
1. Login to GoDaddy account
2. Go to DNS Management for `resilabs.ai`
3. Add CNAME record:
   - **Name**: `s3-auth-api-testnet`
   - **Value**: `$ALB_DNS` (from step 6.2)
   - **TTL**: 600 seconds

#### **8.2 Verify DNS Propagation**
```bash
# Check DNS resolution
nslookup s3-auth-api-testnet.resilabs.ai

# Test with dig
dig s3-auth-api-testnet.resilabs.ai CNAME

# Test API endpoint
curl https://s3-auth-api-testnet.resilabs.ai/healthcheck
```

## 🔧 **Verification and Testing**

### **Health Check Verification**
```bash
# Test health endpoint
curl https://s3-auth-api-testnet.resilabs.ai/healthcheck

# Expected response:
{
  "status": "ok",
  "bucket": "2000-resilabs-test-bittensor-sn428-datacollection",
  "region": "us-east-2",
  "s3_ok": true,
  "redis_ok": true,
  "metagraph_syncer": {
    "enabled": true,
    "netuid": 428,
    "hotkeys_count": 256
  }
}
```

### **API Documentation**
- **Health Check**: https://s3-auth-api-testnet.resilabs.ai/healthcheck
- **API Docs**: https://s3-auth-api-testnet.resilabs.ai/docs
- **Commitment Formats**: https://s3-auth-api-testnet.resilabs.ai/commitment-formats

### **ECS Service Status**
```bash
# Check ECS service status
aws ecs describe-services \
    --cluster subnet428-testnet-cluster \
    --services subnet428-testnet-s3-api-service \
    --region us-east-2 \
    --profile resilabs-admin

# Check target group health
aws elbv2 describe-target-health \
    --target-group-arn $TARGET_GROUP_ARN \
    --profile resilabs-admin
```

## 📊 **Cost Estimation**

**Monthly costs for testnet environment:**
- **ECS Fargate**: ~$15-25 (same as production)
- **Application Load Balancer**: ~$16-20
- **ECR Storage**: ~$1
- **CloudWatch Logs**: ~$2-5
- **ACM Certificate**: Free
- **Secrets Manager**: ~$0.40
- **Total**: ~$35-50/month

## 🔄 **Update Process**

### **Deploy Code Changes**
```bash
# Build new image
docker build -t subnet428-testnet-s3-api:latest .

# Tag and push
docker tag subnet428-testnet-s3-api:latest 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet428-testnet-s3-api:latest
docker push 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet428-testnet-s3-api:latest

# Force new deployment
aws ecs update-service \
    --cluster subnet428-testnet-cluster \
    --service subnet428-testnet-s3-api-service \
    --force-new-deployment \
    --region us-east-2 \
    --profile resilabs-admin
```

## 🔐 **Security Considerations**

### **IAM Permissions Required**
- Same as production deployment
- ECS, ECR, ALB, Route 53, ACM, Secrets Manager
- Refer to `aws/alb-iam-addon.json` for complete permissions

### **Security Groups Summary**
```
ALB Security Group:
- Inbound: HTTP:80, HTTPS:443 from 0.0.0.0/0
- Outbound: All traffic

ECS Security Group:
- Inbound: HTTP:8000 from ALB security group
- Outbound: All traffic
```

## ⚠️ **Important Notes**

1. **Certificate Validation**: Must be done in Route 53, not GoDaddy
2. **DNS Propagation**: Can take 5-30 minutes after CNAME creation
3. **ECS Service**: Must be created before connecting to ALB
4. **Security Groups**: ECS SG must allow traffic from ALB SG
5. **Subnets**: ALB needs at least 2 subnets in different AZs

## 🚨 **Troubleshooting**

### **Common Issues**

**Certificate not validating:**
- Ensure validation CNAME is in Route 53 hosted zone
- Wait 30+ minutes for validation

**ECS service unhealthy:**
- Check security groups allow ALB → ECS traffic
- Verify health check path `/healthcheck` works
- Check ECS task logs in CloudWatch

**DNS not resolving:**
- Verify CNAME record in GoDaddy points to ALB DNS
- Check DNS propagation with `dig` command
- Clear local DNS cache

**ALB returns 503 errors:**
- Check target group has healthy targets
- Verify ECS service is running and registered

## 📞 **Support Resources**

- **Production Guide**: `docs/0001-aws-infrastructure-setup.md`
- **Main Deployment Guide**: `FINAL_DEPLOYMENT_GUIDE.md`
- **AWS Setup Scripts**: `aws/` directory
- **CloudWatch Logs**: `/ecs/subnet428-testnet-s3-api`

---

**Target Completion**: All steps above will result in:
✅ **Live Testnet API**: https://s3-auth-api-testnet.resilabs.ai  
✅ **Subnet 428 Support**: Testnet network configuration  
✅ **Separate Infrastructure**: Independent from production  
✅ **SSL/HTTPS**: Secure connections with valid certificate
