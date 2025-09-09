# Local Testing and Development Guide

**Document ID**: 0002  
**Title**: Local Testing and Development Guide for S3 Storage API  
**Author**: Development Team  
**Date**: December 2024  
**Status**: Active  

## Overview

This document provides a comprehensive guide for setting up, running, and testing the Bittensor Subnet 46 S3 Storage API in a local development environment. It covers the complete testing workflow developed to validate wallet authentication, signature verification, and API functionality.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Network Configuration](#network-configuration)
4. [Testing Workflow](#testing-workflow)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Known Issues and Solutions](#known-issues-and-solutions)
7. [Development Notes](#development-notes)

## Prerequisites

### System Requirements

- Python 3.8+ with virtual environment support
- Redis server (local or remote)
- Valid AWS credentials with S3 access
- Bittensor wallets registered on the target network

### Required Dependencies

The project uses a virtual environment with the following key dependencies:

```bash
# Core dependencies (from requirements.txt)
bittensor>=6.0.0
fastapi
uvicorn
boto3
redis
pydantic
python-dotenv
```

### Wallet Requirements

For testing, you need:
- **Miner wallets**: Registered hotkeys with miner permissions
- **Validator wallets**: Registered hotkeys with validator permissions and sufficient stake
- **Network registration**: Wallets must be registered on the correct network and subnet

## Environment Setup

### 1. Virtual Environment Activation

```bash
# Navigate to project root
cd /path/to/46-resi-labs-api

# Activate virtual environment
source venv/bin/activate

# Set Python path for module imports
export PYTHONPATH=$PWD:$PYTHONPATH
```

### 2. Environment Configuration

Create or update the `.env` file in the project root:

```env
# S3 Configuration
S3_BUCKET=your-bucket-name
S3_REGION=us-east-2

# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here

# Server Configuration
PORT=8000
SERVER_HOST=0.0.0.0

# Network Configuration (CRITICAL - must match wallet registration)
BT_NETWORK=test  # or 'finney' for mainnet
NET_UID=428      # or 46 for production

# Rate Limiting
DAILY_LIMIT_PER_MINER=20
DAILY_LIMIT_PER_VALIDATOR=10000
TOTAL_DAILY_LIMIT=200000

# Timeouts (in seconds)
VALIDATOR_VERIFICATION_TIMEOUT=120
SIGNATURE_VERIFICATION_TIMEOUT=60
S3_OPERATION_TIMEOUT=60

# Metagraph Sync
METAGRAPH_SYNC_INTERVAL=300
```

### 3. Server Startup

```bash
# Start the server with proper module path
PYTHONPATH=$PWD:$PYTHONPATH python s3_storage_api/server.py
```

Expected startup output:
```
Connected to Redis successfully
INFO:__main__:Initializing MetagraphSyncer...
MetagraphSyncer created with config: {428: 300}
Metagraph syncer do_initial_sync called
Initial sync for netuid 428...
Successfully loaded metagraph for 428
INFO:__main__:MetagraphSyncer initialized successfully for netuid 428
INFO:     Started server process [XXXXX]
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Network Configuration

### Network Discovery

The most critical aspect of local testing is ensuring the server is configured for the correct network and subnet where your wallets are registered.

#### Step 1: Identify Your Wallet Network

```bash
# List your wallets
btcli wallets list

# Example output:
# Wallets
# ├── Coldkey 428_testnet_validator  ss58_address 5HTd...
# │   ├── Hotkey 428_testnet_validator_hotkey  ss58_address 5FKi...
# └── Coldkey 428_testnet_miner  ss58_address 5DMR...
#     ├── Hotkey 428_testnet_miner_hotkey  ss58_address 5Dvg...
```

#### Step 2: Find the Correct Network and Subnet

```bash
# Check test network for subnet 428 (common for development)
btcli subnet list --subtensor.network test | grep -A3 -B3 "428\|Resi"

# Check finney (mainnet) for subnet 46 (production)
btcli subnet list --subtensor.network finney | grep -A3 -B3 "46\|Resi"
```

#### Step 3: Verify Wallet Registration

```bash
# Check metagraph for your specific subnet
btcli subnet metagraph --subtensor.network test --netuid 428

# Verify your hotkeys are listed
# Look for your hotkey addresses in the output
```

#### Step 4: Validate Registration Programmatically

```python
import bittensor as bt

# Connect to the network
subtensor = bt.subtensor(network='test')  # or 'finney'
metagraph = subtensor.metagraph(netuid=428)  # or 46

# Check if your hotkeys are registered
your_hotkey = "5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni"
is_registered = your_hotkey in metagraph.hotkeys

print(f"Hotkey {your_hotkey} registered: {is_registered}")

if is_registered:
    idx = metagraph.hotkeys.index(your_hotkey)
    print(f"Position: {idx}")
    print(f"Is validator: {metagraph.validator_permit[idx]}")
    print(f"Stake: {metagraph.S[idx]}")
```

## Testing Workflow

### Phase 1: Health Check Validation

```bash
# Test server health
curl -s http://localhost:8000/healthcheck | jq '.'

# Expected response:
{
  "status": "ok",
  "s3_ok": true,
  "redis_ok": true,
  "metagraph_syncer": {
    "enabled": true,  # or false if fallback methods are used
    "netuid": 428
  }
}
```

### Phase 2: Signature Verification Testing

```bash
# Test signature generation and verification
python api-test/test_signature.py

# Expected output:
# Loading wallet: 428_testnet_validator, hotkey: 428_testnet_validator_hotkey
# Coldkey: 5HTd...
# Hotkey: 5FKi...
# Commitment: s3:data:access:5HTd...:5FKi...:1234567890
# Signature: fc27f1a06424f777...
# Testing signature verification...
# Signature valid: True
# Testing with metagraph directly...
# Hotkey found at index: 4
# Direct keypair verification: True
```

### Phase 3: API Endpoint Testing

#### Miner Access Testing

```bash
# Test miner folder access
python api-test/test_local.py --wallet 428_testnet_miner --hotkey 428_testnet_miner_hotkey --type miner

# Expected successful output:
# ✅ API is healthy!
# ⛏️  Testing miner access...
# ✅ Miner access granted!
#    Folder: data/hotkey=5Dvg.../
#    Upload URL: https://bucket.s3.region.amazonaws.com
```

#### Validator Access Testing

```bash
# Test validator access (requires validator permissions)
python api-test/test_local.py --wallet 428_testnet_validator --hotkey 428_testnet_validator_hotkey --type validator

# Expected successful output:
# 👑 Testing validator access...
# ✅ Validator access granted!
#    Validator Hotkey: 5FKi...
#    Global URLs available: 1
#    Miner URLs available: 1
```

#### Validator Miner-Specific Access

```bash
# Test validator access to specific miner data
python api-test/test_local.py \
  --wallet 428_testnet_validator \
  --hotkey 428_testnet_validator_hotkey \
  --type validator \
  --miner-hotkey 5DvggEsdjznNNvnQ4q6B52JTsSfYCWbCcJRFyMSrYvoZzutr
```

### Phase 4: Direct API Integration Testing

```bash
# Low-level API testing with detailed logging
python api-test/test_direct_api.py

# This test compares local vs server signature verification
# Useful for debugging authentication issues
```

### Phase 5: Production API Testing (Optional)

For testing against the live production API:

```bash
# Test against production API (requires finney network wallets)
python api-test/test_production_api.py --wallet production_wallet --hotkey production_hotkey

# Note: This connects to https://s3-auth-api.resilabs.ai
# Requires wallets registered on finney network, subnet 46
```

## Troubleshooting Guide

### Issue 1: MetagraphSyncer Initialization Failure

**Symptoms:**
```
ERROR:__main__:Failed to initialize MetagraphSyncer: [Errno 65] No route to host
ERROR:__main__:Falling back to original bt_utils functions
```

**Root Cause:** Network connectivity issues or invalid network endpoints.

**Solutions:**
1. **Check Internet Connectivity:**
   ```bash
   ping google.com
   ```

2. **Verify Network Configuration:**
   ```bash
   # Test different networks
   btcli subnet list --subtensor.network test
   btcli subnet list --subtensor.network finney
   ```

3. **Use Fallback Methods:** The server automatically falls back to blockchain verification methods. This is functional but slower.

### Issue 2: Invalid Signature Errors

**Symptoms:**
```
WARNING:server:MINER SIGNATURE FAILED: 5Dvg... (coldkey: 5DMR...)
INFO:     127.0.0.1:59154 - "POST /get-folder-access HTTP/1.1" 401 Unauthorized
```

**Root Causes:**
- Network/subnet mismatch
- Wallet not registered on configured network
- Signature verification method failure

**Diagnostic Steps:**

1. **Verify Local Signature Generation:**
   ```bash
   python api-test/test_signature.py
   # Should show: "Signature valid: True"
   ```

2. **Check Network Configuration Match:**
   ```python
   # In test_signature.py, verify:
   # - Network matches .env BT_NETWORK
   # - Subnet matches .env NET_UID
   # - Hotkey is found in metagraph
   ```

3. **Test Direct API Comparison:**
   ```bash
   python api-test/test_direct_api.py
   # Compare local vs server verification results
   ```

**Solutions:**

1. **Fix Network Mismatch:**
   ```env
   # Update .env to match wallet registration
   BT_NETWORK=test  # Match your wallet's network
   NET_UID=428      # Match your wallet's subnet
   ```

2. **Restart Server After Configuration Changes:**
   ```bash
   # Stop server (Ctrl+C)
   # Restart with new configuration
   PYTHONPATH=$PWD:$PYTHONPATH python s3_storage_api/server.py
   ```

### Issue 3: Validator Permission Denied

**Symptoms:**
```
WARNING:server:VALIDATOR ACCESS DENIED: 5FKi... - not a validator
```

**Root Cause:** Hotkey lacks validator permissions or insufficient stake.

**Verification:**
```python
import bittensor as bt
subtensor = bt.subtensor(network='test')
metagraph = subtensor.metagraph(netuid=428)
hotkey = "5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni"

if hotkey in metagraph.hotkeys:
    idx = metagraph.hotkeys.index(hotkey)
    print(f"Is validator: {metagraph.validator_permit[idx]}")
    print(f"Stake: {metagraph.S[idx]}")
```

**Solutions:**
1. **Test as Miner Instead:** If hotkey lacks validator permissions, test miner endpoints
2. **Check Stake Requirements:** Ensure sufficient stake for validator permissions
3. **Verify Registration:** Confirm hotkey is registered with correct permissions

### Issue 4: Hotkey Not Found in Subnet

**Symptoms:**
```
Error connecting to Bittensor network: [Errno 65] No route to host
Hotkey 5FKi... is not registered in subnet 46
```

**Root Cause:** Server looking in wrong subnet or network.

**Solution:**
1. **Find Correct Subnet:**
   ```bash
   # Search all subnets for your hotkey
   btcli subnet list --subtensor.network test | grep -A5 -B5 "Resi"
   btcli subnet list --subtensor.network finney | grep -A5 -B5 "Resi"
   ```

2. **Update Configuration:**
   ```env
   # Update .env with correct values
   BT_NETWORK=test
   NET_UID=428  # Use the subnet where your hotkey is registered
   ```

## Known Issues and Solutions

### 1. Address Already in Use Error

**Error:**
```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000): [errno 48] address already in use
```

**Solution:**
```bash
# Find and kill existing server process
ps aux | grep server.py
kill [PROCESS_ID]

# Or use port-specific kill
lsof -ti:8000 | xargs kill -9
```

### 2. Module Import Errors

**Error:**
```
ModuleNotFoundError: No module named 's3_storage_api'
```

**Solution:**
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH=$PWD:$PYTHONPATH

# Or run as module
python -m s3_storage_api.server
```

### 3. Password Prompts During Testing

**Behavior:** Tests prompt for wallet passwords repeatedly.

**Solutions:**
1. **Use Unencrypted Test Wallets** (development only)
2. **Cache Passwords** in environment variables (not recommended for production)
3. **Use Hardware Wallets** for production testing

### 4. Network Timeout Issues

**Symptoms:** Long delays or timeouts during blockchain operations.

**Configuration:** The server has built-in timeout protection:
```env
VALIDATOR_VERIFICATION_TIMEOUT=120  # 2 minutes
SIGNATURE_VERIFICATION_TIMEOUT=60   # 1 minute
S3_OPERATION_TIMEOUT=60             # 1 minute
```

**Solutions:**
1. **Increase Timeouts** for slower networks
2. **Use Cached Verification** when metagraph syncer is working
3. **Test with Different Networks** (test vs finney)

## Development Notes

### Testing Strategy

The testing suite follows a layered approach:

1. **Unit Testing**: Individual signature verification (`test_signature.py`)
2. **Integration Testing**: API endpoint testing (`test_local.py`)
3. **System Testing**: End-to-end workflow validation (`test_direct_api.py`)

### Network Environment Management

Different environments require different configurations:

```bash
# Development (testnet)
BT_NETWORK=test
NET_UID=428

# Staging (testnet with production-like data)
BT_NETWORK=test
NET_UID=428

# Production (mainnet)
BT_NETWORK=finney
NET_UID=46
```

### Security Considerations

1. **Never commit wallet files** to version control
2. **Use environment variables** for sensitive configuration
3. **Test with minimal stake** on testnets
4. **Rotate AWS credentials** regularly
5. **Monitor API rate limits** during testing

### Performance Optimization

1. **Metagraph Caching**: When working, provides ~1ms verification vs seconds for blockchain calls
2. **Connection Pooling**: Redis and S3 clients use connection pooling
3. **Timeout Protection**: Prevents hanging operations from blocking the server
4. **Rate Limiting**: Protects against abuse and excessive usage

### Future Improvements

1. **Automated Test Suite**: Integration with CI/CD pipelines
2. **Mock Network Testing**: Local blockchain simulation for isolated testing
3. **Performance Benchmarking**: Automated performance regression testing
4. **Multi-Network Testing**: Simultaneous testing across different networks

## Conclusion

This testing framework provides comprehensive validation of the S3 Storage API functionality. The key to successful testing is ensuring proper network and subnet configuration alignment with wallet registration. The layered testing approach allows for quick identification and resolution of issues at different levels of the system.

For ongoing development, maintain this testing suite and update it as new features are added to the API. Regular testing across different network conditions and wallet configurations ensures robust operation in production environments.
