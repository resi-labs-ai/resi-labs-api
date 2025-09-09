#!/bin/bash

# Update ECS service to use the manually created ALB
# Run this after creating the ALB in AWS Console

set -e

AWS_REGION="us-east-2"
ECS_CLUSTER_NAME="subnet46-cluster"
ECS_SERVICE_NAME="subnet46-s3-api-service"

# Get the target group ARN (replace with actual ARN from console)
TARGET_GROUP_ARN="arn:aws:elasticloadbalancing:us-east-2:532533045818:targetgroup/subnet46-tg/85890b8d75c6c2bb"

echo "🔄 Updating ECS service to use ALB..."

# Update ECS service to use the target group
aws ecs update-service \
    --cluster ${ECS_CLUSTER_NAME} \
    --service ${ECS_SERVICE_NAME} \
    --load-balancers targetGroupArn=${TARGET_GROUP_ARN},containerName=api,containerPort=8000 \
    --region ${AWS_REGION}

echo "✅ ECS service updated!"
echo ""
echo "🔧 Next steps:"
echo "1. Wait 5-10 minutes for ALB to become healthy"
echo "2. Get ALB DNS name from AWS Console"
echo "3. Add CNAME record to GoDaddy pointing to ALB DNS"
echo "4. Test: curl https://s3-auth-api.resilabs.ai/healthcheck"
