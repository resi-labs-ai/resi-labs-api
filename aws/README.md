# AWS Setup Files for Subnet 46 S3 API

This directory contains AWS-specific setup scripts and configuration files used to deploy the Subnet 46 S3 API infrastructure.

## 📁 **Files in this Directory**

### **Setup Scripts**
- **`setup-custom-domain.sh`** - Complete ALB and custom domain setup script
  - Creates Application Load Balancer
  - Configures security groups
  - Sets up HTTPS listeners with SSL certificates
  - Provides GoDaddy DNS configuration instructions

- **`update-ecs-alb.sh`** - Connect ECS service to ALB
  - Updates ECS service to use the load balancer
  - Connects containers to target group
  - Used after manual ALB creation

### **IAM Configuration**
- **`alb-iam-addon.json`** - IAM permissions for ALB creation
  - Required permissions for load balancer operations
  - EC2 networking permissions
  - Certificate and Route 53 access
  - Service-linked role creation

## 🚀 **Usage**

### **For Initial Deployment**
1. **Set up IAM permissions** (add `alb-iam-addon.json` to your deployment user)
2. **Run ALB setup**: `./setup-custom-domain.sh`
3. **Update ECS service**: `./update-ecs-alb.sh`

### **For Manual ALB Creation** (if script fails)
1. **Create ALB manually** in AWS Console
2. **Get target group ARN** from console
3. **Update `update-ecs-alb.sh`** with real ARN
4. **Run**: `./update-ecs-alb.sh`

## 🔐 **Prerequisites**

- AWS CLI configured with appropriate permissions
- SSL certificate validated in ACM
- ECS service already running
- Route 53 hosted zone (for certificate validation)

## 📋 **Current Infrastructure**

**Created by these scripts:**
- Application Load Balancer: `subnet46-alb`
- Target Group: `subnet46-tg` 
- Security Groups: `subnet46-alb-sg`, `subnet46-api-sg`
- HTTPS listener with SSL certificate
- ECS service integration

**Live Endpoint:** https://s3-auth-api.resilabs.ai

## ⚠️ **Important Notes**

- Scripts require specific IAM permissions (see `alb-iam-addon.json`)
- SSL certificate must be validated before running setup
- Scripts are designed for us-east-2 region
- Manual ALB creation through console may be easier than CLI approach

## 📞 **Support**

For issues with these AWS setup scripts, refer to:
- `../docs/0001-aws-infrastructure-setup.md` - Complete infrastructure documentation
- `../FINAL_DEPLOYMENT_GUIDE.md` - Full deployment guide with troubleshooting
