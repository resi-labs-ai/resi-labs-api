#!/bin/bash

# Setup custom domain for Subnet 46 S3 API
# This creates an Application Load Balancer and points your subdomain to it

set -e

# Configuration - UPDATE THESE VALUES
DOMAIN_NAME="s3-auth-api.resilabs.ai"     # Your S3 auth API subdomain
HOSTED_ZONE_ID="Z0114515IKPREXJRDQ2C"            # Your Route 53 hosted zone ID
CERTIFICATE_ARN="arn:aws:acm:us-east-2:532533045818:certificate/13bf13b3-0e3b-4e56-97ec-319a3c7edcd0"  # SSL certificate ARN

AWS_REGION="us-east-2"
ECS_CLUSTER_NAME="subnet46-cluster"
ECS_SERVICE_NAME="subnet46-s3-api-service"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🌐 Setting up custom domain for Subnet 46 S3 API${NC}"

# Get account ID and VPC info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region ${AWS_REGION})
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --query 'Subnets[].SubnetId' --output text --region ${AWS_REGION})

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "   Domain: ${DOMAIN_NAME}"
echo "   VPC: ${VPC_ID}"
echo "   Subnets: ${SUBNET_IDS}"

# Step 1: Create security group for ALB
echo -e "${YELLOW}🛡️  Creating ALB security group...${NC}"
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name subnet46-alb-sg \
    --description "Security group for Subnet 46 ALB" \
    --vpc-id ${VPC_ID} \
    --region ${AWS_REGION} \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups --filters "Name=group-name,Values=subnet46-alb-sg" --query 'SecurityGroups[0].GroupId' --output text --region ${AWS_REGION})

# Allow HTTP and HTTPS traffic to ALB
aws ec2 authorize-security-group-ingress \
    --group-id ${ALB_SG_ID} \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region ${AWS_REGION} 2>/dev/null || echo "HTTP rule exists"

aws ec2 authorize-security-group-ingress \
    --group-id ${ALB_SG_ID} \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region ${AWS_REGION} 2>/dev/null || echo "HTTPS rule exists"

# Step 2: Update ECS service security group to allow ALB traffic
echo -e "${YELLOW}🔧 Updating ECS security group...${NC}"
ECS_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=subnet46-api-sg" --query 'SecurityGroups[0].GroupId' --output text --region ${AWS_REGION})

# Allow traffic from ALB to ECS service
aws ec2 authorize-security-group-ingress \
    --group-id ${ECS_SG_ID} \
    --protocol tcp \
    --port 8000 \
    --source-group ${ALB_SG_ID} \
    --region ${AWS_REGION} 2>/dev/null || echo "ALB to ECS rule exists"

# Step 3: Create Application Load Balancer
echo -e "${YELLOW}🏗️  Creating Application Load Balancer...${NC}"

# Check if ALB already exists
ALB_ARN=$(aws elbv2 describe-load-balancers --names subnet46-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text --region ${AWS_REGION} 2>/dev/null)

if [ "$ALB_ARN" = "None" ] || [ -z "$ALB_ARN" ]; then
    echo "   Creating new ALB..."
    # Convert subnet IDs to array and take first 2 (ALB requires at least 2 AZs)
    SUBNET_ARRAY=(${SUBNET_IDS})
    ALB_SUBNETS="${SUBNET_ARRAY[0]} ${SUBNET_ARRAY[1]}"
    
    echo "   Using subnets: ${ALB_SUBNETS}"
    
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name subnet46-alb \
        --subnets ${ALB_SUBNETS} \
        --security-groups ${ALB_SG_ID} \
        --region ${AWS_REGION} \
        --query 'LoadBalancers[0].LoadBalancerArn' --output text)
    
    if [ $? -eq 0 ]; then
        echo "   ✅ ALB created successfully"
    else
        echo "   ❌ ALB creation failed"
        exit 1
    fi
else
    echo "   Using existing ALB..."
fi

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns ${ALB_ARN} --query 'LoadBalancers[0].DNSName' --output text --region ${AWS_REGION})

echo "   ALB DNS: ${ALB_DNS}"

# Step 4: Create target group
echo -e "${YELLOW}🎯 Creating target group...${NC}"
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name subnet46-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id ${VPC_ID} \
    --target-type ip \
    --health-check-path /healthcheck \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region ${AWS_REGION} \
    --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || \
    aws elbv2 describe-target-groups --names subnet46-tg --query 'TargetGroups[0].TargetGroupArn' --output text --region ${AWS_REGION})

# Step 5: Create listeners
echo -e "${YELLOW}👂 Creating ALB listeners...${NC}"

# HTTP listener (redirect to HTTPS)
aws elbv2 create-listener \
    --load-balancer-arn ${ALB_ARN} \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}' \
    --region ${AWS_REGION} 2>/dev/null || echo "HTTP listener exists"

# HTTPS listener (requires SSL certificate)
if [ ! -z "${CERTIFICATE_ARN}" ] && [ "${CERTIFICATE_ARN}" != "arn:aws:acm:us-east-2:532533045818:certificate/your-cert-arn" ]; then
    aws elbv2 create-listener \
        --load-balancer-arn ${ALB_ARN} \
        --protocol HTTPS \
        --port 443 \
        --certificates CertificateArn=${CERTIFICATE_ARN} \
        --default-actions Type=forward,TargetGroupArn=${TARGET_GROUP_ARN} \
        --region ${AWS_REGION} 2>/dev/null || echo "HTTPS listener exists"
else
    echo "⚠️  SSL Certificate ARN not provided - creating HTTP-only listener"
    aws elbv2 create-listener \
        --load-balancer-arn ${ALB_ARN} \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=${TARGET_GROUP_ARN} \
        --region ${AWS_REGION} 2>/dev/null || echo "HTTP listener exists"
fi

# Step 6: Update ECS service to use ALB
echo -e "${YELLOW}🔄 Updating ECS service to use ALB...${NC}"
aws ecs update-service \
    --cluster ${ECS_CLUSTER_NAME} \
    --service ${ECS_SERVICE_NAME} \
    --load-balancers targetGroupArn=${TARGET_GROUP_ARN},containerName=api,containerPort=8000 \
    --region ${AWS_REGION}

# Step 7: Manual GoDaddy DNS setup instructions
echo -e "${YELLOW}📍 GoDaddy DNS Setup Required${NC}"
echo ""
echo -e "${YELLOW}🔧 Manual Steps for GoDaddy:${NC}"
echo "   1. Login to GoDaddy Domain Manager"
echo "   2. Go to resilabs.ai → DNS Management"
echo "   3. Add a new CNAME record:"
echo ""
echo -e "${GREEN}      Record Type: CNAME${NC}"
echo -e "${GREEN}      Name: s3-auth-api${NC}"
echo -e "${GREEN}      Value: ${ALB_DNS}${NC}"
echo -e "${GREEN}      TTL: 1 Hour (or default)${NC}"
echo ""
echo "   4. Save the record"
echo "   5. Wait 5-15 minutes for DNS propagation"
echo ""
echo -e "${YELLOW}⚠️  Important: Use the ALB DNS name above, not an IP address!${NC}"

echo ""
echo -e "${GREEN}🎉 Load Balancer setup complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Summary:${NC}"
echo "   ALB DNS: ${ALB_DNS}"
echo "   Target Group: ${TARGET_GROUP_ARN}"
echo "   Custom Domain: ${DOMAIN_NAME}"
echo ""
echo -e "${YELLOW}🔧 Next Steps:${NC}"
echo "   1. Wait 5-10 minutes for ALB to become active"
echo "   2. Test ALB directly: curl http://${ALB_DNS}/healthcheck"
echo "   3. Add CNAME record to GoDaddy (instructions above)"
echo "   4. Wait for DNS propagation (5-15 minutes)"
echo "   5. Test custom domain: curl https://${DOMAIN_NAME}/healthcheck"
echo "   6. Update your miners/validators to use: https://${DOMAIN_NAME}"
echo ""
echo -e "${YELLOW}💡 Benefits:${NC}"
echo "   ✅ Stable URL (no more changing IP addresses)"
echo "   ✅ SSL/HTTPS support"
echo "   ✅ Health checks and auto-recovery"
echo "   ✅ Load balancing for future scaling"
