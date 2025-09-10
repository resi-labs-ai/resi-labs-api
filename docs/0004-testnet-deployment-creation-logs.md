I'll help you create a comprehensive guide for deploying the same API server on testnet (subnet 428). This will be a complete step-by-step guide that covers everything from AWS setup to domain configuration.

[16 tools called]

Perfect! I've created a comprehensive testnet deployment guide and all the necessary files for deploying your API on Subnet 428 testnet. Here's what I've created:

## 📚 **Complete Testnet Documentation & Scripts**

### **Main Guide**: `docs/0002-testnet-deployment-guide.md`
**Complete 280-line deployment guide covering:**
- ✅ **Step-by-step process** - From AWS setup to DNS configuration
- ✅ **Key differences** - Subnet 428 vs 46 configuration table
- ✅ **Infrastructure overview** - All AWS resources needed
- ✅ **SSL certificate setup** - ACM certificate and validation
- ✅ **Load balancer configuration** - ALB, target groups, security groups
- ✅ **DNS setup** - Route 53 validation + GoDaddy CNAME
- ✅ **Cost breakdown** - ~$35-50/month (same as production)
- ✅ **Troubleshooting section** - Common issues and solutions

### **Configuration Files Created:**
- ✅ **`.example.env.testnet`** - Environment template for subnet 428
- ✅ **`docker-compose.testnet.yml`** - Local testnet development
- ✅ **`aws/testnet-task-definition.json`** - ECS task definition
- ✅ **`aws/cors-config.json`** - S3 CORS configuration

### **Deployment Scripts:**
- ✅ **`aws/deploy-testnet.sh`** - Main deployment script (executable)
- ✅ **`aws/setup-testnet-alb.sh`** - ALB setup with SSL (executable)  
- ✅ **`aws/testnet-README.md`** - Quick reference for scripts

## 🎯 **Key Testnet Configuration**

| Setting | Value |
|---------|-------|
| **Subnet ID** | 428 |
| **Network** | test |
| **Domain** | s3-auth-api-testnet.resilabs.ai |
| **S3 Bucket** | 2000-resilabs-test-bittensor-sn428-datacollection |
| **ECS Cluster** | subnet428-testnet-cluster |
| **ALB Name** | subnet428-testnet-alb |

## 🚀 **Quick Start Process**

```bash
# 1. Configure environment
cp .example.env.testnet .env.testnet
# Edit .env.testnet with your AWS credentials

# 2. Deploy infrastructure
./aws/deploy-testnet.sh

# 3. Request SSL certificate
aws acm request-certificate \
    --domain-name s3-auth-api-testnet.resilabs.ai \
    --validation-method DNS \
    --region us-east-2

# 4. Add validation CNAME to Route 53
# (Get from certificate details)

# 5. Setup ALB with SSL (after certificate is ISSUED)
./aws/setup-testnet-alb.sh arn:aws:acm:us-east-2:532533045818:certificate/your-cert-id

# 6. Add CNAME in GoDaddy
# Name: s3-auth-api-testnet
# Value: <ALB-DNS-NAME>
```

## 📁 **Updated File Structure**

```
46-resi-labs-api/
├── aws/                                    # AWS deployment scripts
│   ├── deploy-testnet.sh                   # NEW: Main testnet deployment
│   ├── setup-testnet-alb.sh               # NEW: Testnet ALB setup
│   ├── testnet-task-definition.json       # NEW: ECS task definition
│   ├── cors-config.json                   # NEW: S3 CORS config
│   ├── testnet-README.md                  # NEW: Testnet scripts guide
│   ├── setup-custom-domain.sh             # Production ALB setup
│   ├── update-ecs-alb.sh                  # Production ECS update
│   ├── alb-iam-addon.json                 # IAM permissions
│   └── README.md                          # AWS scripts overview
├── docs/                                   # Documentation
│   ├── 0001-aws-infrastructure-setup.md   # Production infrastructure
│   └── 0002-testnet-deployment-guide.md   # NEW: Complete testnet guide
├── .example.env.testnet                    # NEW: Testnet env template
├── docker-compose.testnet.yml              # NEW: Testnet local dev
└── ... (existing production files)
```

## ✨ **Key Features**

- **🔄 Parallel Infrastructure**: Completely separate from production
- **🔐 SSL Ready**: Automated certificate and ALB setup
- **📊 Monitoring**: CloudWatch logs and health checks
- **🛡️ Security**: Proper security groups and IAM roles
- **📱 Scripts**: Automated deployment with error handling
- **📚 Documentation**: Step-by-step guides with troubleshooting

## 🎉 **Ready to Deploy!**

Your testnet deployment is now fully documented and scripted. The process will create:
- **Live API**: https://s3-auth-api-testnet.resilabs.ai
- **Health Check**: https://s3-auth-api-testnet.resilabs.ai/healthcheck  
- **API Docs**: https://s3-auth-api-testnet.resilabs.ai/docs

The scripts handle all the complex AWS setup automatically, and the guide provides manual steps where needed (like DNS configuration in GoDaddy). Everything is designed to be completely separate from your production environment while following the same proven architecture! 🚀