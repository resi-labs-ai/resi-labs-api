#!/bin/bash

# Testnet ALB Setup Script for Subnet 428
# Sets up Application Load Balancer with SSL for testnet domain

set -e

# Configuration
REGION="us-east-2"
ACCOUNT_ID="532533045818"
DOMAIN_NAME="s3-auth-api-testnet.resilabs.ai"
CLUSTER_NAME="subnet428-testnet-cluster"
SERVICE_NAME="subnet428-testnet-s3-api-service"
ALB_NAME="subnet428-testnet-alb"
TARGET_GROUP_NAME="subnet428-testnet-tg"
ALB_SG_NAME="subnet428-testnet-alb-sg"
ECS_SG_NAME="subnet428-testnet-api-sg"

echo "🔧 Setting up Application Load Balancer for Testnet"
echo "===================================================="

# Check if certificate ARN is provided
if [ -z "$1" ]; then
    echo "❌ Usage: $0 <CERTIFICATE_ARN>"
    echo "Example: $0 arn:aws:acm:us-east-2:532533045818:certificate/your-cert-id"
    echo ""
    echo "To get your certificate ARN:"
    echo "aws acm list-certificates --region $REGION --query 'CertificateSummaryList[?DomainName==\`$DOMAIN_NAME\`].CertificateArn' --output text"
    exit 1
fi

CERTIFICATE_ARN="$1"

echo "📋 Configuration:"
echo "  Domain: $DOMAIN_NAME"
echo "  Certificate: $CERTIFICATE_ARN"
echo "  Region: $REGION"
echo ""

# Verify certificate exists and is issued
echo "🔐 Verifying SSL certificate..."
CERT_STATUS=$(aws acm describe-certificate --certificate-arn "$CERTIFICATE_ARN" --region $REGION --query 'Certificate.Status' --output text)

if [ "$CERT_STATUS" != "ISSUED" ]; then
    echo "❌ Certificate status is: $CERT_STATUS"
    echo "Certificate must be ISSUED before proceeding."
    exit 1
fi

echo "✅ SSL certificate is valid and issued"

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)
echo "🏠 Using VPC: $VPC_ID"

# Create ALB Security Group
echo "🛡️ Creating ALB security group..."
if aws ec2 describe-security-groups --filters "Name=group-name,Values=$ALB_SG_NAME" --region $REGION --query 'SecurityGroups[0].GroupId' --output text | grep -q "sg-"; then
    ALB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$ALB_SG_NAME" --region $REGION --query 'SecurityGroups[0].GroupId' --output text)
    echo "✅ ALB security group already exists: $ALB_SG_ID"
else
    ALB_SG_ID=$(aws ec2 create-security-group \
        --group-name $ALB_SG_NAME \
        --description "Security group for Subnet 428 testnet ALB" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' --output text)
    
    # Allow HTTP and HTTPS traffic
    aws ec2 authorize-security-group-ingress \
        --group-id $ALB_SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $ALB_SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    echo "✅ ALB security group created: $ALB_SG_ID"
fi

# Create ECS Security Group
echo "🛡️ Creating ECS security group..."
if aws ec2 describe-security-groups --filters "Name=group-name,Values=$ECS_SG_NAME" --region $REGION --query 'SecurityGroups[0].GroupId' --output text | grep -q "sg-"; then
    ECS_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$ECS_SG_NAME" --region $REGION --query 'SecurityGroups[0].GroupId' --output text)
    echo "✅ ECS security group already exists: $ECS_SG_ID"
else
    ECS_SG_ID=$(aws ec2 create-security-group \
        --group-name $ECS_SG_NAME \
        --description "Security group for Subnet 428 testnet ECS tasks" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' --output text)
    
    # Allow traffic from ALB on port 8000
    aws ec2 authorize-security-group-ingress \
        --group-id $ECS_SG_ID \
        --protocol tcp \
        --port 8000 \
        --source-group $ALB_SG_ID \
        --region $REGION
    
    # Also allow from anywhere for testing (can be removed later)
    aws ec2 authorize-security-group-ingress \
        --group-id $ECS_SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    echo "✅ ECS security group created: $ECS_SG_ID"
fi

# Get subnets for ALB (need at least 2 in different AZs)
SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[].SubnetId' \
    --output text \
    --region $REGION | tr '\t' ' ')

SUBNET_ARRAY=($SUBNET_IDS)
if [ ${#SUBNET_ARRAY[@]} -lt 2 ]; then
    echo "❌ Need at least 2 subnets in different AZs for ALB"
    exit 1
fi

SUBNET_1=${SUBNET_ARRAY[0]}
SUBNET_2=${SUBNET_ARRAY[1]}

echo "🌐 Using subnets: $SUBNET_1, $SUBNET_2"

# Create Application Load Balancer
echo "⚖️ Creating Application Load Balancer..."
if aws elbv2 describe-load-balancers --names $ALB_NAME --region $REGION > /dev/null 2>&1; then
    ALB_ARN=$(aws elbv2 describe-load-balancers --names $ALB_NAME --region $REGION --query 'LoadBalancers[0].LoadBalancerArn' --output text)
    ALB_DNS=$(aws elbv2 describe-load-balancers --names $ALB_NAME --region $REGION --query 'LoadBalancers[0].DNSName' --output text)
    echo "✅ ALB already exists: $ALB_NAME"
else
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name $ALB_NAME \
        --subnets $SUBNET_1 $SUBNET_2 \
        --security-groups $ALB_SG_ID \
        --scheme internet-facing \
        --type application \
        --ip-address-type ipv4 \
        --region $REGION \
        --query 'LoadBalancers[0].LoadBalancerArn' --output text)
    
    ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --region $REGION --query 'LoadBalancers[0].DNSName' --output text)
    echo "✅ ALB created: $ALB_NAME"
fi

echo "🌐 ALB DNS Name: $ALB_DNS"

# Create Target Group
echo "🎯 Creating target group..."
if aws elbv2 describe-target-groups --names $TARGET_GROUP_NAME --region $REGION > /dev/null 2>&1; then
    TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups --names $TARGET_GROUP_NAME --region $REGION --query 'TargetGroups[0].TargetGroupArn' --output text)
    echo "✅ Target group already exists: $TARGET_GROUP_NAME"
else
    TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
        --name $TARGET_GROUP_NAME \
        --protocol HTTP \
        --port 8000 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-path /healthcheck \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 3 \
        --region $REGION \
        --query 'TargetGroups[0].TargetGroupArn' --output text)
    
    echo "✅ Target group created: $TARGET_GROUP_NAME"
fi

# Create HTTPS Listener
echo "🔐 Creating HTTPS listener..."
LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=$CERTIFICATE_ARN \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --region $REGION \
    --query 'Listeners[0].ListenerArn' --output text 2>/dev/null || echo "exists")

if [ "$LISTENER_ARN" != "exists" ]; then
    echo "✅ HTTPS listener created"
else
    echo "✅ HTTPS listener already exists"
fi

# Update ECS Service to use Load Balancer
echo "🔗 Connecting ECS service to load balancer..."

# Get current subnets from ECS service
CURRENT_SUBNETS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION \
    --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
    --output text | tr '\t' ',')

if [ "$CURRENT_SUBNETS" = "" ]; then
    CURRENT_SUBNETS="$SUBNET_1,$SUBNET_2"
fi

aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --load-balancers targetGroupArn=$TARGET_GROUP_ARN,containerName=subnet428-testnet-api,containerPort=8000 \
    --network-configuration "awsvpcConfiguration={subnets=[$CURRENT_SUBNETS],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
    --region $REGION > /dev/null

echo "✅ ECS service connected to load balancer"

# Wait for service to stabilize
echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION

echo "✅ Service is stable"

echo ""
echo "🎉 ALB Setup Complete!"
echo "====================="
echo ""
echo "📋 Summary:"
echo "  ALB DNS Name: $ALB_DNS"
echo "  Target Group: $TARGET_GROUP_ARN"
echo "  SSL Certificate: $CERTIFICATE_ARN"
echo ""
echo "🌐 Next Steps:"
echo "1. Add CNAME record in GoDaddy:"
echo "   Name: s3-auth-api-testnet"
echo "   Value: $ALB_DNS"
echo "   TTL: 600"
echo ""
echo "2. Wait for DNS propagation (5-30 minutes)"
echo ""
echo "3. Test endpoints:"
echo "   curl https://$DOMAIN_NAME/healthcheck"
echo "   curl https://$DOMAIN_NAME/docs"
echo ""
echo "4. Monitor target group health:"
echo "   aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --region $REGION"
