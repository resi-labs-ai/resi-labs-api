#!/bin/bash

# Testnet Deployment Script for Subnet 428
# This script deploys the S3 API to AWS testnet environment

set -e

# Configuration
REGION="us-east-2"
ACCOUNT_ID="532533045818"
CLUSTER_NAME="subnet428-testnet-cluster"
SERVICE_NAME="subnet428-testnet-s3-api-service"
REPOSITORY_NAME="subnet428-testnet-s3-api"
FAMILY_NAME="subnet428-testnet-s3-api"
LOG_GROUP="/ecs/subnet428-testnet-s3-api"
SECRET_NAME="subnet428-testnet/aws-credentials"

echo "🚀 Starting Testnet Deployment for Subnet 428"
echo "================================================"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✅ AWS CLI configured"

# Step 1: Create ECR Repository
echo "📦 Creating ECR repository..."
if aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $REGION > /dev/null 2>&1; then
    echo "✅ ECR repository already exists"
else
    aws ecr create-repository \
        --repository-name $REPOSITORY_NAME \
        --region $REGION
    echo "✅ ECR repository created"
fi

# Step 2: Build and Push Docker Image
echo "🐳 Building and pushing Docker image..."

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build image
docker build -t $REPOSITORY_NAME:latest .

# Tag for ECR
docker tag $REPOSITORY_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest

# Push to ECR
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:latest

echo "✅ Docker image pushed to ECR"

# Step 3: Create CloudWatch Log Group
echo "📊 Creating CloudWatch log group..."
if aws logs describe-log-groups --log-group-name-prefix $LOG_GROUP --region $REGION | grep -q $LOG_GROUP; then
    echo "✅ Log group already exists"
else
    aws logs create-log-group \
        --log-group-name $LOG_GROUP \
        --region $REGION
    echo "✅ CloudWatch log group created"
fi

# Step 4: Create ECS Cluster
echo "🏗️ Creating ECS cluster..."
if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $REGION | grep -q "ACTIVE"; then
    echo "✅ ECS cluster already exists"
else
    aws ecs create-cluster \
        --cluster-name $CLUSTER_NAME \
        --region $REGION
    echo "✅ ECS cluster created"
fi

# Step 5: Register Task Definition
echo "📋 Registering task definition..."
aws ecs register-task-definition \
    --cli-input-json file://aws/testnet-task-definition.json \
    --region $REGION

echo "✅ Task definition registered"

# Step 6: Create ECS Service (if doesn't exist)
echo "🔧 Creating ECS service..."

# Get default VPC and subnets
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[].SubnetId' --output text --region $REGION | tr '\t' ',')

if aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION | grep -q "ACTIVE"; then
    echo "✅ ECS service already exists, updating..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $REGION
else
    echo "🆕 Creating new ECS service..."
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $FAMILY_NAME \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[],assignPublicIp=ENABLED}" \
        --region $REGION
fi

echo "✅ ECS service ready"

# Step 7: Get Service Public IP
echo "🌐 Getting service public IP..."
sleep 30  # Wait for service to start

TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $REGION --query 'taskArns[0]' --output text)

if [ "$TASK_ARN" != "None" ] && [ "$TASK_ARN" != "" ]; then
    ENI_ID=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --region $REGION --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
    
    if [ "$ENI_ID" != "" ]; then
        PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
        
        if [ "$PUBLIC_IP" != "None" ] && [ "$PUBLIC_IP" != "" ]; then
            echo "📍 Public IP: $PUBLIC_IP"
            echo "🏥 Health Check: http://$PUBLIC_IP:8000/healthcheck"
            echo "📚 API Documentation: http://$PUBLIC_IP:8000/docs"
        else
            echo "⚠️ Public IP not yet available. Service may still be starting."
        fi
    fi
fi

echo ""
echo "🎉 Testnet deployment completed!"
echo "================================================"
echo "Next steps:"
echo "1. Set up SSL certificate for s3-auth-api-testnet.resilabs.ai"
echo "2. Create Application Load Balancer"
echo "3. Configure DNS in GoDaddy"
echo "4. Run health checks"
echo ""
echo "Use './aws/setup-testnet-alb.sh' for load balancer setup"
