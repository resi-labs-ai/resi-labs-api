#!/bin/bash

# Certificate Monitoring Script for Testnet Deployment
# This script monitors SSL certificate validation progress

CERTIFICATE_ARN="arn:aws:acm:us-east-2:532533045818:certificate/12570075-740a-4dda-a9f5-2d4689432bec"
VALIDATION_RECORD="_b48eacf7025e6af43d465718b2a851df.s3-auth-api-testnet.resilabs.ai"

echo "🔍 Monitoring SSL Certificate Validation"
echo "========================================"
echo "Certificate ARN: $CERTIFICATE_ARN"
echo "Validation Record: $VALIDATION_RECORD"
echo ""

# Function to check certificate status
check_cert_status() {
    aws acm describe-certificate \
        --certificate-arn $CERTIFICATE_ARN \
        --region us-east-2 \
        --profile resilabs-admin \
        --query 'Certificate.{Status:Status,ValidationStatus:DomainValidationOptions[0].ValidationStatus}' \
        --output table 2>/dev/null
}

# Function to check DNS resolution
check_dns() {
    echo "🌐 Checking DNS resolution:"
    if dig $VALIDATION_RECORD CNAME +short | grep -q "acm-validations.aws"; then
        echo "✅ DNS validation record is resolving correctly"
        return 0
    else
        echo "⏳ DNS validation record not yet propagated"
        return 1
    fi
}

# Main monitoring loop
counter=0
max_checks=60  # Check for up to 30 minutes (every 30 seconds)

while [ $counter -lt $max_checks ]; do
    echo "📊 Check #$((counter + 1)) at $(date '+%H:%M:%S')"
    
    # Check DNS first
    check_dns
    dns_ready=$?
    
    # Check certificate status
    echo "🔐 Certificate Status:"
    cert_status=$(check_cert_status)
    echo "$cert_status"
    
    # Extract just the status
    status=$(echo "$cert_status" | grep -E "ISSUED|PENDING_VALIDATION|FAILED" | head -1 | awk '{print $NF}')
    
    case $status in
        "ISSUED")
            echo ""
            echo "🎉 SUCCESS! Certificate has been ISSUED!"
            echo "✅ You can now continue with the next steps in your deployment."
            echo ""
            echo "Next step: Create ECS Task Definition (Phase 5)"
            exit 0
            ;;
        "FAILED")
            echo ""
            echo "❌ FAILED! Certificate validation failed."
            echo "Please check the DNS record in GoDaddy and try again."
            exit 1
            ;;
        "PENDING_VALIDATION")
            if [ $dns_ready -eq 0 ]; then
                echo "⏳ DNS is ready, waiting for AWS to validate..."
            else
                echo "⏳ Waiting for DNS propagation..."
            fi
            ;;
        *)
            echo "⏳ Status: $status"
            ;;
    esac
    
    echo ""
    echo "Waiting 30 seconds before next check..."
    sleep 30
    counter=$((counter + 1))
done

echo "⏰ Timeout reached after 30 minutes."
echo "Certificate may still be validating. Check manually with:"
echo "aws acm describe-certificate --certificate-arn $CERTIFICATE_ARN --region us-east-2 --profile resilabs-admin --query 'Certificate.Status'"
