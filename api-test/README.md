# S3 Storage API Testing Suite

This directory contains comprehensive testing tools for the Bittensor Subnet 46 S3 Storage API. These tests were developed to validate wallet authentication, signature verification, and API functionality with local development environments.

## 🚀 Quick Start

### Prerequisites

1. **Running S3 Storage API Server** - The server must be running locally on `http://localhost:8000`
2. **Valid Bittensor Wallets** - You need registered wallets on the appropriate network
3. **Correct Network Configuration** - Server must be configured for the right network and subnet

### Environment Setup

1. Activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Ensure PYTHONPATH includes the project root:
   ```bash
   export PYTHONPATH=$PWD:$PYTHONPATH
   ```

3. Start the server:
   ```bash
   python s3_storage_api/server.py
   ```

## 📋 Test Files Overview

### `test_local.py` - Main Testing Script
**Purpose**: Comprehensive testing of miner and validator access endpoints

**Usage**:
```bash
# Test miner access
python api-test/test_local.py --wallet WALLET_NAME --hotkey HOTKEY_NAME --type miner

# Test validator access
python api-test/test_local.py --wallet WALLET_NAME --hotkey HOTKEY_NAME --type validator

# Test validator access to specific miner data
python api-test/test_local.py --wallet VALIDATOR_WALLET --hotkey VALIDATOR_HOTKEY --type validator --miner-hotkey TARGET_MINER_HOTKEY
```

**Features**:
- ✅ Health check validation
- ✅ Wallet loading and signature generation
- ✅ API request testing with proper error handling
- ✅ Support for both miner and validator workflows
- ✅ Detailed output with troubleshooting information

### `test_signature.py` - Signature Verification Testing
**Purpose**: Manual signature verification to debug authentication issues

**Usage**:
```bash
python api-test/test_signature.py
```

**What it tests**:
- Wallet loading and key extraction
- Commitment string generation
- Signature creation and verification
- Metagraph hotkey validation
- Direct keypair verification

### `test_direct_api.py` - Direct API Integration Testing
**Purpose**: Low-level API testing with manual signature verification

**Usage**:
```bash
python api-test/test_direct_api.py
```

**Features**:
- Direct HTTP requests to API endpoints
- Local signature verification comparison
- Detailed request/response logging
- Error diagnosis and troubleshooting

### `test_production_api.py` - Production API Testing
**Purpose**: Testing against the live production API at `https://s3-auth-api.resilabs.ai`

**Usage**:
```bash
python api-test/test_production_api.py --wallet WALLET_NAME --hotkey HOTKEY_NAME
```

**Features**:
- Production endpoint testing with DNS resolution
- Comprehensive API endpoint coverage
- Production wallet validation
- Real S3 bucket interaction testing

**Note**: This test connects to the live production API and requires wallets registered on the production network (finney, subnet 46).

### `test_mainnet_s3_auth.py` - Mainnet User Test Script
**Purpose**: Simple, user-friendly test script for mainnet miners and validators to verify their setup

**Usage**:
```bash
python api-test/test_mainnet_s3_auth.py --wallet WALLET_NAME --hotkey HOTKEY_NAME
```

**Features**:
- Colorized, user-friendly output
- Step-by-step verification process
- Clear success/failure indicators
- Detailed troubleshooting information
- Designed for end-users (miners/validators)

**Note**: This is the recommended script for miners and validators to test their setup before participating in subnet 46.

## 🔧 Configuration Requirements

### Network and Subnet Configuration

The API server must be configured with the correct network and subnet in the `.env` file:

```env
# For testnet subnet 428 (Resi Labs test network)
BT_NETWORK=test
NET_UID=428

# For mainnet subnet 46 (Resi Labs production)
BT_NETWORK=finney
NET_UID=46
```

### AWS Configuration

Ensure your `.env` file contains valid AWS credentials:

```env
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
S3_BUCKET=your-bucket-name
S3_REGION=us-east-2
```

## 🐛 Troubleshooting Guide

### Common Issues and Solutions

#### 1. "Invalid signature" Error
**Symptoms**: API returns 401 with "Invalid signature" message
**Causes**:
- Network mismatch (server on different network than wallet)
- Metagraph syncer initialization failure
- Network connectivity issues

**Solutions**:
1. Verify network configuration matches wallet registration
2. Check server logs for "No route to host" errors
3. Ensure hotkey is registered in the correct subnet
4. Test signature verification locally with `test_signature.py`

#### 2. "You are not validator" Error
**Symptoms**: Validator access denied even with registered hotkey
**Causes**:
- Hotkey registered as miner, not validator
- Insufficient stake for validator permissions
- Wrong subnet configuration

**Solutions**:
1. Check hotkey permissions: `btcli subnet metagraph --netuid SUBNET_ID`
2. Verify validator stake and permissions
3. Test as miner instead if hotkey lacks validator permissions

#### 3. "Hotkey not registered" Error
**Symptoms**: Server reports hotkey not found in subnet
**Causes**:
- Wrong subnet ID in server configuration
- Wrong network in server configuration
- Hotkey not actually registered

**Solutions**:
1. List available subnets: `btcli subnet list --subtensor.network NETWORK`
2. Check metagraph: `btcli subnet metagraph --netuid SUBNET_ID`
3. Verify wallet registration status

#### 4. Connection Errors
**Symptoms**: "No route to host" or connection timeouts
**Causes**:
- Network connectivity issues
- Firewall blocking connections
- Invalid network endpoints

**Solutions**:
1. Check internet connectivity
2. Verify network endpoints are accessible
3. Test with different networks (test vs finney)

## 📊 Example Test Session

Here's a complete example of testing with subnet 428 on the test network:

```bash
# 1. Check your wallets
btcli wallets list

# 2. Verify subnet registration
btcli subnet list --subtensor.network test | grep -A5 -B5 "428\|Resi"

# 3. Check metagraph
btcli subnet metagraph --subtensor.network test --netuid 428

# 4. Configure server (.env file)
BT_NETWORK=test
NET_UID=428

# 5. Start server
source venv/bin/activate
PYTHONPATH=$PWD:$PYTHONPATH python s3_storage_api/server.py

# 6. Test miner access
python api-test/test_local.py --wallet 428_testnet_miner --hotkey 428_testnet_miner_hotkey --type miner

# 7. Debug signature if needed
python api-test/test_signature.py

# 8. Test direct API
python api-test/test_direct_api.py
```

## 🎯 Expected Results

### Successful Miner Test
```
🚀 Starting S3 Auth API Local Tests
==================================================
🏥 Testing healthcheck endpoint...
✅ API is healthy!
   Status: ok
   S3 OK: True
   Redis OK: True
   Metagraph Syncer: True

==================================================
⛏️  Testing miner access for wallet: your_wallet, hotkey: your_hotkey
   Coldkey: 5ABC...XYZ
   Hotkey: 5DEF...123
   Commitment: s3:data:access:5ABC...XYZ:5DEF...123:1234567890
   Making API request...
✅ Miner access granted!
   Folder: data/hotkey=5DEF...123/
   Upload URL: https://bucket.s3.region.amazonaws.com
   Expiry: 2023-12-25T12:00:00
   List URL: https://...

==================================================
✅ Tests completed successfully!
```

### Successful Validator Test
```
👑 Testing validator access for wallet: validator_wallet, hotkey: validator_hotkey
   Hotkey: 5GHI...456
   Commitment: s3:validator:access:1234567890
   Making API request...
✅ Validator access granted!
   Validator Hotkey: 5GHI...456
   Bucket: your-bucket-name
   Region: us-east-2
   Expiry: 2023-12-25T12:00:00
   Global URLs available: 1
   Miner URLs available: 1
```

## 🔍 Network Discovery

Use these commands to discover the correct network and subnet configuration:

```bash
# List all subnets on test network
btcli subnet list --subtensor.network test

# List all subnets on finney (mainnet)
btcli subnet list --subtensor.network finney

# Find Resi Labs subnets
btcli subnet list --subtensor.network test | grep -i resi
btcli subnet list --subtensor.network finney | grep -i resi

# Check specific subnet details
btcli subnet metagraph --subtensor.network test --netuid 428
btcli subnet metagraph --subtensor.network finney --netuid 46
```

## 📝 Notes

- **Wallet Passwords**: Tests will prompt for wallet passwords when loading encrypted keys
- **Network Latency**: Blockchain operations may take time; the server has timeout protection
- **Rate Limiting**: API has daily limits per miner/validator to prevent abuse
- **Development vs Production**: Always test on testnet before using production networks
- **Security**: Never commit wallet files or passwords to version control

## 🤝 Contributing

When adding new tests:

1. Follow the existing naming convention: `test_*.py`
2. Include comprehensive error handling and user feedback
3. Add documentation for new test scenarios
4. Test with both miner and validator workflows
5. Update this README with new test descriptions

## 📞 Support

If you encounter issues:

1. Check the server logs for detailed error messages
2. Run the signature verification test to isolate issues
3. Verify network and subnet configuration
4. Ensure wallets are properly registered
5. Check AWS credentials and S3 bucket access

For persistent issues, review the server configuration and network connectivity.
