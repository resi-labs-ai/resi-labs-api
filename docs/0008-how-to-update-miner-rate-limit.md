# Updating API Rate Limits in Production

## Overview

This guide documents how to update API rate limits in production without full redeployment, and how to prevent availability zone issues that can cause deployment failures.

## Quick Reference

**Current Production Rate Limits:**
- **Miner**: 100 requests/day (5x increase from 20)
- **Validator**: 10,000 requests/day
- **Total Daily**: 200,000 requests/day

## Prerequisites

- AWS CLI configured with appropriate permissions
- Access to ECS cluster: `subnet46-cluster`
- Access to ECS service: `subnet46-s3-api-service`
- Load balancer: `subnet46-alb` (enabled in `us-east-2a` and `us-east-2b`)

## Step-by-Step Process

### 1. Update Task Definition

Edit the production task definition file:

```bash
# Edit the task definition
vim aws/production-task-definition.json
```

Update the rate limit environment variables:

```json
{
  "environment": [
    {"name": "DAILY_LIMIT_PER_MINER", "value": "100"},
    {"name": "DAILY_LIMIT_PER_VALIDATOR", "value": "10000"},
    {"name": "TOTAL_DAILY_LIMIT", "value": "200000"}
  ]
}
```

### 2. Register New Task Definition

```bash
aws ecs register-task-definition \
  --cli-input-json file://aws/production-task-definition.json \
  --region us-east-2
```

### 3. Update ECS Service

**CRITICAL**: Always ensure the ECS service uses only the availability zones enabled for the load balancer.

```bash
# First, check which AZs are enabled for the load balancer
aws elbv2 describe-load-balancers \
  --region us-east-2 \
  --query 'LoadBalancers[?LoadBalancerName==`subnet46-alb`].AvailabilityZones[].ZoneName' \
  --output text

# Update the service with correct subnets (only AZs enabled for ALB)
aws ecs update-service \
  --cluster subnet46-cluster \
  --service subnet46-s3-api-service \
  --task-definition subnet46-s3-api-task:3 \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-0c3412270b089f592,subnet-0855b0d1532237c26],securityGroups=[sg-0cfcee039256f1007],assignPublicIp=ENABLED}" \
  --health-check-grace-period-seconds 120 \
  --region us-east-2
```

### 4. Verify Deployment

```bash
# Check deployment status
aws ecs describe-services \
  --cluster subnet46-cluster \
  --services subnet46-s3-api-service \
  --region us-east-2 \
  --query 'services[0].deployments[0].{status:status,rolloutState:rolloutState,runningCount:runningCount,desiredCount:desiredCount}'

# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-2:532533045818:targetgroup/subnet46-tg/85890b8d75c6c2bb \
  --region us-east-2

# Test the API
curl -s https://s3-auth-api.resilabs.ai/rate-limits | python3 -m json.tool
```

## Preventing Availability Zone Issues

### The Problem

The most common deployment failure occurs when:
1. ECS service is configured to use all available subnets (including `us-east-2c`)
2. Load balancer is only enabled for specific availability zones (`us-east-2a` and `us-east-2b`)
3. New tasks get placed in unsupported AZs and fail health checks

### The Solution

**Always ensure ECS service subnets match load balancer availability zones.**

#### Check Load Balancer AZs

```bash
aws elbv2 describe-load-balancers \
  --region us-east-2 \
  --query 'LoadBalancers[?LoadBalancerName==`subnet46-alb`].AvailabilityZones[].ZoneName' \
  --output text
```

#### Check ECS Service Subnets

```bash
aws ecs describe-services \
  --cluster subnet46-cluster \
  --services subnet46-s3-api-service \
  --region us-east-2 \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
  --output text
```

#### Map Subnets to AZs

```bash
aws ec2 describe-subnets \
  --subnet-ids subnet-0c3412270b089f592 subnet-0855b0d1532237c26 subnet-0bc9102dd49970a20 \
  --region us-east-2 \
  --query 'Subnets[].{SubnetId:SubnetId,AvailabilityZone:AvailabilityZone}' \
  --output table
```

### Best Practices

1. **Always verify AZ compatibility** before deploying
2. **Use placement constraints** if needed to force specific AZs
3. **Monitor target group health** during deployments
4. **Set appropriate health check grace periods** (120+ seconds)
5. **Test with small changes first** before major updates

## Troubleshooting

### Common Issues

#### 1. "Target is in an Availability Zone that is not enabled for the load balancer"

**Cause**: ECS service using subnets in AZs not enabled for ALB

**Solution**: Update ECS service to use only ALB-enabled AZs

```bash
aws ecs update-service \
  --cluster subnet46-cluster \
  --service subnet46-s3-api-service \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-0c3412270b089f592,subnet-0855b0d1532237c26],securityGroups=[sg-0cfcee039256f1007],assignPublicIp=ENABLED}" \
  --region us-east-2
```

#### 2. Health Check Failures

**Cause**: Insufficient grace period for application startup

**Solution**: Increase health check grace period

```bash
aws ecs update-service \
  --cluster subnet46-cluster \
  --service subnet46-s3-api-service \
  --health-check-grace-period-seconds 120 \
  --region us-east-2
```

#### 3. Deployment Stuck in Progress

**Cause**: New tasks failing to start or pass health checks

**Solution**: Force new deployment with correct configuration

```bash
aws ecs update-service \
  --cluster subnet46-cluster \
  --service subnet46-s3-api-service \
  --force-new-deployment \
  --region us-east-2
```

### Monitoring Commands

```bash
# Check service events
aws ecs describe-services \
  --cluster subnet46-cluster \
  --services subnet46-s3-api-service \
  --region us-east-2 \
  --query 'services[0].events[0:10].{createdAt:createdAt,message:message}'

# Check running tasks
aws ecs list-tasks \
  --cluster subnet46-cluster \
  --service-name subnet46-s3-api-service \
  --region us-east-2

# Check task details
aws ecs describe-tasks \
  --cluster subnet46-cluster \
  --tasks <TASK_ARN> \
  --region us-east-2 \
  --query 'tasks[0].{taskDefinitionArn:taskDefinitionArn,lastStatus:lastStatus,healthStatus:healthStatus}'
```

## Environment Variables Reference

### Rate Limiting Variables

| Variable | Description | Default | Production |
|----------|-------------|---------|------------|
| `DAILY_LIMIT_PER_MINER` | Requests per day per miner | 20 | 100 |
| `DAILY_LIMIT_PER_VALIDATOR` | Requests per day per validator | 10,000 | 10,000 |
| `TOTAL_DAILY_LIMIT` | Total requests per day for all users | 200,000 | 200,000 |
| `ENABLE_RATE_LIMITING` | Enable/disable rate limiting | true | true |
| `RATE_LIMIT_PER_MINUTE` | Requests per minute | 60 | 60 |

### Other Important Variables

| Variable | Description | Value |
|----------|-------------|-------|
| `BT_NETWORK` | Bittensor network | finney |
| `NET_UID` | Subnet UID | 46 |
| `S3_BUCKET` | S3 bucket name | 4000-resilabs-prod-bittensor-sn46-datacollection |
| `S3_REGION` | S3 region | us-east-2 |
| `PORT` | API port | 8000 |

## Network Configuration

### Current Production Setup

- **Load Balancer**: `subnet46-alb`
- **Enabled AZs**: `us-east-2a`, `us-east-2b`
- **ECS Subnets**: `subnet-0c3412270b089f592` (us-east-2a), `subnet-0855b0d1532237c26` (us-east-2b)
- **Security Group**: `sg-0cfcee039256f1007`
- **Target Group**: `arn:aws:elasticloadbalancing:us-east-2:532533045818:targetgroup/subnet46-tg/85890b8d75c6c2bb`

### Subnet Mapping

| Subnet ID | Availability Zone | Status |
|-----------|------------------|--------|
| `subnet-0c3412270b089f592` | us-east-2a | ✅ Enabled for ALB |
| `subnet-0855b0d1532237c26` | us-east-2b | ✅ Enabled for ALB |
| `subnet-0bc9102dd49970a20` | us-east-2c | ❌ Not enabled for ALB |

## Success Criteria

A successful deployment should show:

1. **Service Status**: `ACTIVE` with `runningCount` = `desiredCount`
2. **Deployment Status**: `PRIMARY` with `rolloutState` = `COMPLETED`
3. **Target Health**: All targets in `healthy` state
4. **API Response**: Rate limits showing updated values
5. **Zero Downtime**: Old task continues serving while new task starts

## Rollback Procedure

If deployment fails:

```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster subnet46-cluster \
  --service subnet46-s3-api-service \
  --task-definition subnet46-s3-api-task:2 \
  --region us-east-2

# Force new deployment if needed
aws ecs update-service \
  --cluster subnet46-cluster \
  --service subnet46-s3-api-service \
  --force-new-deployment \
  --region us-east-2
```

## Notes

- Rate limits reset daily at midnight UTC
- Changes take effect immediately for new requests
- Monitor CloudWatch logs for any issues
- Always test in staging environment first
- Keep task definition revisions for easy rollback
