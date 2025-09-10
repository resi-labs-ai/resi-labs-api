# Testnet Deployment Scripts for Subnet 428

This directory contains scripts and configuration files specifically for deploying the Subnet 428 testnet API.

## 🚀 **Quick Start**

### **Prerequisites**
1. AWS CLI configured with appropriate permissions
2. Docker running locally
3. Copy `.example.env.testnet` to `.env.testnet` and configure

### **Deploy Testnet API**
```bash
# 1. Deploy basic infrastructure
./aws/deploy-testnet.sh

# 2. Request SSL certificate
aws acm request-certificate \
    --domain-name s3-auth-api-testnet.resilabs.ai \
    --validation-method DNS \
    --region us-east-2

# 3. Add validation CNAME to Route 53 (get from certificate details)

# 4. Setup ALB with SSL (after certificate is ISSUED)
./aws/setup-testnet-alb.sh arn:aws:acm:us-east-2:532533045818:certificate/your-cert-id

# 5. Add CNAME in GoDaddy pointing to ALB DNS name
```

## 📁 **Files in this Directory**

### **Deployment Scripts**
- **`deploy-testnet.sh`** - Main deployment script
  - Creates ECR repository
  - Builds and pushes Docker image
  - Sets up ECS cluster and service
  - Creates CloudWatch logs

- **`setup-testnet-alb.sh`** - Load balancer setup
  - Creates ALB with security groups
  - Sets up target group and HTTPS listener
  - Connects ECS service to ALB

### **Configuration Files**
- **`testnet-task-definition.json`** - ECS task definition for subnet 428
- **`cors-config.json`** - S3 CORS configuration
- **`testnet-README.md`** - This file

### **Environment Templates**
- **`../.example.env.testnet`** - Environment variables template
- **`../docker-compose.testnet.yml`** - Local testnet development

## 🎯 **Target Infrastructure**

**Created Resources:**
- ECS Cluster: `subnet428-testnet-cluster`
- ECS Service: `subnet428-testnet-s3-api-service`
- ECR Repository: `subnet428-testnet-s3-api`
- ALB: `subnet428-testnet-alb`
- Target Group: `subnet428-testnet-tg`
- Security Groups: `subnet428-testnet-alb-sg`, `subnet428-testnet-api-sg`
- CloudWatch Logs: `/ecs/subnet428-testnet-s3-api`

**Final Endpoint:** https://s3-auth-api-testnet.resilabs.ai

## 🔧 **Configuration**

### **Testnet Settings**
- **Subnet ID**: 428
- **Network**: test (Bittensor testnet)
- **S3 Bucket**: `2000-resilabs-test-bittensor-sn428-datacollection`
- **Region**: us-east-2

### **Domain Setup**
1. **SSL Certificate**: Request in ACM for `s3-auth-api-testnet.resilabs.ai`
2. **DNS Validation**: Add CNAME to Route 53 hosted zone
3. **Domain CNAME**: Add in GoDaddy pointing to ALB DNS

## 🔐 **Security**

**IAM Permissions Required:**
- Same as production (see `alb-iam-addon.json`)
- ECS, ECR, ALB, Route 53, ACM, Secrets Manager

**Security Groups:**
```
ALB Security Group:
- Inbound: HTTP:80, HTTPS:443 from 0.0.0.0/0
- Outbound: All traffic

ECS Security Group:
- Inbound: HTTP:8000 from ALB + 0.0.0.0/0 (testing)
- Outbound: All traffic
```

## 📊 **Monitoring**

### **Health Checks**
```bash
# Check ECS service
aws ecs describe-services --cluster subnet428-testnet-cluster --services subnet428-testnet-s3-api-service

# Check target group health
aws elbv2 describe-target-health --target-group-arn <TARGET_GROUP_ARN>

# Test API endpoints
curl https://s3-auth-api-testnet.resilabs.ai/healthcheck
curl https://s3-auth-api-testnet.resilabs.ai/docs
```

### **Logs**
```bash
# View ECS logs
aws logs tail /ecs/subnet428-testnet-s3-api --follow

# Get recent logs
aws logs describe-log-streams --log-group-name /ecs/subnet428-testnet-s3-api
```

## 🔄 **Updates**

### **Deploy Code Changes**
```bash
# Rebuild and push image
./aws/deploy-testnet.sh

# Or manual update
docker build -t subnet428-testnet-s3-api:latest .
docker tag subnet428-testnet-s3-api:latest 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet428-testnet-s3-api:latest
docker push 532533045818.dkr.ecr.us-east-2.amazonaws.com/subnet428-testnet-s3-api:latest

aws ecs update-service \
    --cluster subnet428-testnet-cluster \
    --service subnet428-testnet-s3-api-service \
    --force-new-deployment
```

### **Update Task Definition**
```bash
# Modify testnet-task-definition.json
# Then register new revision
aws ecs register-task-definition --cli-input-json file://aws/testnet-task-definition.json

# Update service to use new revision
aws ecs update-service \
    --cluster subnet428-testnet-cluster \
    --service subnet428-testnet-s3-api-service \
    --task-definition subnet428-testnet-s3-api
```

## ⚠️ **Important Notes**

1. **Separate from Production**: All resources have `testnet` in the name
2. **Certificate Validation**: Must be done in Route 53, not GoDaddy
3. **DNS Setup**: Requires both validation CNAME and domain CNAME
4. **Cost**: Similar to production (~$35-50/month)
5. **Testing**: Use testnet miners/validators for testing

## 🚨 **Troubleshooting**

### **Common Issues**

**Service won't start:**
```bash
# Check task logs
aws ecs describe-tasks --cluster subnet428-testnet-cluster --tasks <TASK_ARN>
aws logs tail /ecs/subnet428-testnet-s3-api --follow
```

**ALB returns 503:**
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn <TARGET_GROUP_ARN>
```

**DNS not resolving:**
```bash
# Check CNAME record
dig s3-auth-api-testnet.resilabs.ai CNAME
nslookup s3-auth-api-testnet.resilabs.ai
```

**Certificate not validating:**
- Ensure validation CNAME is in Route 53
- Wait 30+ minutes for validation
- Check certificate status in ACM console

## 📞 **Support**

For issues with testnet deployment:
- **Main Guide**: `docs/0002-testnet-deployment-guide.md`
- **Production Reference**: `docs/0001-aws-infrastructure-setup.md`
- **AWS Console**: Monitor ECS, ALB, and CloudWatch directly
