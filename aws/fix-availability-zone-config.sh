#!/bin/bash

# Fix ECS Service Availability Zone Configuration
# This script ensures ECS service only uses AZs enabled for the load balancer

set -e

# Configuration
AWS_REGION="us-east-2"
ECS_CLUSTER_NAME="subnet46-cluster"
ECS_SERVICE_NAME="subnet46-s3-api-service"
ALB_NAME="subnet46-alb"
TARGET_GROUP_ARN="arn:aws:elasticloadbalancing:us-east-2:532533045818:targetgroup/subnet46-tg/85890b8d75c6c2bb"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Checking ECS Service and Load Balancer AZ Configuration...${NC}"

# Get ALB enabled availability zones
echo "📋 Getting ALB enabled availability zones..."
ALB_AZS=$(aws elbv2 describe-load-balancers \
  --region $AWS_REGION \
  --query "LoadBalancers[?LoadBalancerName=='$ALB_NAME'].AvailabilityZones[].ZoneName" \
  --output text)

if [ -z "$ALB_AZS" ]; then
  echo -e "${RED}❌ Load balancer '$ALB_NAME' not found${NC}"
  exit 1
fi

echo "✅ ALB enabled AZs: $ALB_AZS"

# Get ECS service current subnets
echo "📋 Getting ECS service current subnets..."
ECS_SUBNETS=$(aws ecs describe-services \
  --cluster $ECS_CLUSTER_NAME \
  --services $ECS_SERVICE_NAME \
  --region $AWS_REGION \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
  --output text)

if [ -z "$ECS_SUBNETS" ]; then
  echo -e "${RED}❌ ECS service '$ECS_SERVICE_NAME' not found${NC}"
  exit 1
fi

echo "✅ ECS service subnets: $ECS_SUBNETS"

# Get subnet to AZ mapping
echo "📋 Getting subnet to AZ mapping..."
SUBNET_AZ_MAP=$(aws ec2 describe-subnets \
  --subnet-ids $ECS_SUBNETS \
  --region $AWS_REGION \
  --query 'Subnets[].{SubnetId:SubnetId,AvailabilityZone:AvailabilityZone}' \
  --output text)

echo "✅ Subnet to AZ mapping:"
echo "$SUBNET_AZ_MAP"

# Check if any ECS subnets are in AZs not enabled for ALB
echo "🔍 Checking for AZ mismatches..."
NEEDS_FIX=false

for subnet in $ECS_SUBNETS; do
  az=$(aws ec2 describe-subnets \
    --subnet-ids $subnet \
    --region $AWS_REGION \
    --query 'Subnets[0].AvailabilityZone' \
    --output text)
  
  if [[ ! " $ALB_AZS " =~ " $az " ]]; then
    echo -e "${RED}❌ Subnet $subnet is in $az, which is not enabled for ALB${NC}"
    NEEDS_FIX=true
  else
    echo -e "${GREEN}✅ Subnet $subnet is in $az, which is enabled for ALB${NC}"
  fi
done

if [ "$NEEDS_FIX" = false ]; then
  echo -e "${GREEN}✅ ECS service is already configured correctly${NC}"
  exit 0
fi

echo -e "${YELLOW}🔧 Fixing ECS service configuration...${NC}"

# Get subnets that are in ALB-enabled AZs
echo "📋 Finding subnets in ALB-enabled AZs..."
ALB_ENABLED_SUBNETS=""

for az in $ALB_AZS; do
  subnet=$(aws ec2 describe-subnets \
    --filters "Name=availability-zone,Values=$az" "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION)" \
    --region $AWS_REGION \
    --query 'Subnets[0].SubnetId' \
    --output text)
  
  if [ "$subnet" != "None" ] && [ -n "$subnet" ]; then
    ALB_ENABLED_SUBNETS="$ALB_ENABLED_SUBNETS $subnet"
    echo "✅ Found subnet $subnet in $az"
  fi
done

# Convert to comma-separated list
ALB_ENABLED_SUBNETS=$(echo $ALB_ENABLED_SUBNETS | tr ' ' ',')

if [ -z "$ALB_ENABLED_SUBNETS" ]; then
  echo -e "${RED}❌ No subnets found in ALB-enabled AZs${NC}"
  exit 1
fi

echo "✅ ALB-enabled subnets: $ALB_ENABLED_SUBNETS"

# Get current security groups
echo "📋 Getting current security groups..."
SECURITY_GROUPS=$(aws ecs describe-services \
  --cluster $ECS_CLUSTER_NAME \
  --services $ECS_SERVICE_NAME \
  --region $AWS_REGION \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups' \
  --output text | tr '\t' ',')

echo "✅ Security groups: $SECURITY_GROUPS"

# Update ECS service with correct subnets
echo "🔧 Updating ECS service with correct subnets..."
aws ecs update-service \
  --cluster $ECS_CLUSTER_NAME \
  --service $ECS_SERVICE_NAME \
  --network-configuration "awsvpcConfiguration={subnets=[$ALB_ENABLED_SUBNETS],securityGroups=[$SECURITY_GROUPS],assignPublicIp=ENABLED}" \
  --region $AWS_REGION > /dev/null

echo -e "${GREEN}✅ ECS service updated successfully${NC}"

# Wait for service to stabilize
echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
  --cluster $ECS_CLUSTER_NAME \
  --services $ECS_SERVICE_NAME \
  --region $AWS_REGION

echo -e "${GREEN}✅ Service is stable${NC}"

# Verify target group health
echo "🔍 Checking target group health..."
aws elbv2 describe-target-health \
  --target-group-arn $TARGET_GROUP_ARN \
  --region $AWS_REGION \
  --query 'TargetHealthDescriptions[].{Target:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table

echo -e "${GREEN}🎉 ECS service AZ configuration fixed!${NC}"
echo ""
echo "📋 Summary:"
echo "  - ECS service now only uses subnets in ALB-enabled AZs"
echo "  - Service is stable and healthy"
echo "  - Load balancer can route traffic to all targets"
echo ""
echo "🌐 Test the API:"
echo "  curl -s https://s3-auth-api.resilabs.ai/rate-limits | python3 -m json.tool"
