# 🧪 Subnet 428 Testnet S3 API Testing Guide for Miners & Validators

**Ready to test on Bittensor Subnet 428 testnet?** Use this guide to test your wallet authentication and verify you can access the testnet S3 storage system.

## ⚡ Quick Start (2 Minutes)

### **Standard Testing (Recommended)**
```bash
# 1. Download the testnet test script
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_testnet_s3_auth.py

# 2. Create Virtual Environment if Python and Pip are not global
python -m venv venv
source venv/bin/activate

# 3. Install requirements
pip install bittensor requests

# 4. Test your testnet setup (you'll be prompted for password only once)
python test_testnet_s3_auth.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

# Optional: Check validator status only
python test_testnet_s3_auth.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME --validator-check-only
```

### **🔒 Security Variants Available**
Choose based on your security requirements:

```bash
# STANDARD (1 password prompt) - Good for development/testing
python test_testnet_s3_auth.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY

# SECURE (2 password prompts) - Recommended for production
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_testnet_s3_auth_secure.py
python test_testnet_s3_auth_secure.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY

# MAXIMUM SECURITY (3 password prompts) - High-security environments
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_testnet_s3_auth_maxsec.py
python test_testnet_s3_auth_maxsec.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY
```

## 📋 What You Need

- **Registered Hotkey**: Your hotkey must be registered on **testnet subnet 428**
- **Python 3.8+** with `bittensor` and `requests` packages
- **Wallet Access**: Your wallet files and password (if encrypted)
- **Testnet TAO**: Free testnet tokens for registration and staking

### For Validators
- **Validator Permissions**: Sufficient testnet stake (typically 100+ testnet TAO) and validator permit
- **Additional Access**: Validators get read access to all miner data

### For Miners  
- **Any Registration**: Any registered hotkey on testnet subnet 428 can mine
- **Upload Access**: You'll get credentials to upload data to your dedicated folder

## ✅ Expected Success Output

When your testnet test passes, you'll see:

```
============================================================
                   S3 Auth API Testnet Test              
============================================================

✅ Testnet API is healthy!
✅ Wallet loaded successfully!
✅ Hotkey is registered! (Position: 3, Stake: 50.0000 testnet TAO)
✅ Miner access granted! 🎉
   Your S3 folder: data/hotkey=5DEF456...ABC123/
   Upload URL: https://2000-resilabs-test-bittensor-sn428-datacollection.s3.us-east-2.amazonaws.com
   Access expires: 2024-12-26T15:30:00

✅ 🎉 SUCCESS! Your wallet can authenticate with the Testnet S3 API
✅ You're ready to participate in subnet 428 testnet!
```

## 🔧 Quick Troubleshooting

### ❌ "Hotkey not registered"
```bash
# Register on testnet subnet 428
btcli subnet register --subtensor.network test --netuid 428 --wallet.name YOUR_WALLET --wallet.hotkey YOUR_HOTKEY

# Verify registration
btcli subnet metagraph --subtensor.network test --netuid 428
```

### ❌ "Cannot connect to API"
- Check internet connection
- Verify testnet API is running: `curl https://s3-auth-api-testnet.resilabs.ai/healthcheck`
- Try again later (testnet API might be temporarily down)
- Run with `--skip-health` to bypass health check

### ❌ "Wallet loading failed"
- Verify wallet name and hotkey name: `btcli wallets list`
- Check wallet files exist: `ls ~/.bittensor/wallets/`
- Ensure correct wallet password

### ❌ "You are not validator"
- Your hotkey is registered as a miner, not validator
- You can still mine! The test will check miner access instead
- To become a validator, you need sufficient testnet stake and validator permissions

### ❌ "Need testnet TAO"
```bash
# Get free testnet TAO from faucet (multiple options)
btcli wallet faucet --wallet.name YOUR_WALLET --subtensor.network test

# Alternative: Web-based faucet
# Visit: https://app.minersunion.ai/testnet-faucet

# Check your balance
btcli wallet balance --wallet.name YOUR_WALLET --subtensor.network test
```

### ❌ "Am I a validator?"
```bash
# Check your validator status (works with all security variants)
python test_testnet_s3_auth.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY --validator-check-only
python test_testnet_s3_auth_secure.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY --validator-check-only
python test_testnet_s3_auth_maxsec.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY --validator-check-only

# Or check manually
btcli subnet metagraph --subtensor.network test --netuid 428
```

### ❌ "Which security level should I use?"
- **Development/Testing**: Use **Standard** version (1 password, most convenient)
- **Production Scripts**: Use **Secure** version (2 passwords, good balance)
- **High-Security**: Use **Max Security** version (3 passwords, zero caching)
- **All versions tested and working** ✅

## 🎯 What This Test Validates

✅ **Wallet Setup**: Your wallet files work correctly  
✅ **Testnet Registration**: You're registered on testnet subnet 428  
✅ **API Authentication**: You can authenticate with the testnet S3 API  
✅ **S3 Credentials**: You receive valid upload/access credentials for testnet bucket  
✅ **Permissions**: Confirms your miner/validator status on testnet  

## 📊 Testnet API Information

- **Live Testnet API**: `https://s3-auth-api-testnet.resilabs.ai`
- **Network**: Bittensor Testnet
- **Subnet**: 428 (Resi Labs Testnet)
- **Testnet Bucket**: `2000-resilabs-test-bittensor-sn428-datacollection`
- **Bucket Structure**: `data/hotkey={your_hotkey}/job_id={job_id}/`

## 🔒 Security Levels Comparison

| Version | Security Level | Password Prompts | Caching | Best For |
|---------|---------------|------------------|---------|----------|
| **Standard** | Medium | 1x | Full wallet + addresses | Development/Testing |
| **Secure** | High | 2x | Only public addresses | Production |
| **Max Security** | Maximum | 3x | None | High-Security Environments |

### **Security Details:**
- **Standard**: Caches wallet object and addresses for convenience
- **Secure**: Only caches public addresses, reloads wallet for signing
- **Max Security**: No caching, wallet reloaded for every operation

## 🆚 Testnet vs Production Differences

| Feature | Production (Subnet 46) | Testnet (Subnet 428) |
|---------|----------------------|---------------------|
| **API URL** | `s3-auth-api.resilabs.ai` | `s3-auth-api-testnet.resilabs.ai` |
| **Network** | `finney` (mainnet) | `test` (testnet) |
| **Subnet ID** | `46` | `428` |
| **TAO Required** | Real TAO | Free testnet TAO |
| **S3 Bucket** | Production bucket | Test bucket |
| **Data Persistence** | Permanent | May be reset |
| **Security Variants** | Available | Available |

## 🔗 Additional Resources

- **Full Documentation**: [GitHub Repository](https://github.com/resi-labs-ai/resi-labs-api)
- **Testnet API Health**: [https://s3-auth-api-testnet.resilabs.ai/healthcheck](https://s3-auth-api-testnet.resilabs.ai/healthcheck)
- **Testnet API Docs**: [https://s3-auth-api-testnet.resilabs.ai/docs](https://s3-auth-api-testnet.resilabs.ai/docs)
- **Production Guide**: `MINER_VALIDATOR_TESTING_GUIDE.md`
- **Testnet Deployment**: `docs/0005-testnet-deployment-guide.md`

### **📥 Download Security Variants:**
```bash
# Standard version (already included in repo)
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_testnet_s3_auth.py

# Secure version
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_testnet_s3_auth_secure.py

# Maximum security version
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_testnet_s3_auth_maxsec.py

# Security comparison tool
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/security_comparison.py
python security_comparison.py  # View comparison table
```

## 🚀 Getting Started on Testnet

### **Step 1: Get Testnet TAO**
```bash
# Option 1: CLI Faucet
btcli wallet faucet --wallet.name YOUR_WALLET --subtensor.network test

# Option 2: Web Faucet (Recommended)
# Visit: https://app.minersunion.ai/testnet-faucet
# Enter your coldkey address and request testnet TAO

# Verify balance
btcli wallet balance --wallet.name YOUR_WALLET --subtensor.network test
```

### **Step 2: Register as Miner**
```bash
# Register your hotkey on testnet subnet 428
btcli subnet register --subtensor.network test --netuid 428 --wallet.name YOUR_WALLET --wallet.hotkey YOUR_HOTKEY

# Verify registration
btcli subnet metagraph --subtensor.network test --netuid 428
```

### **Step 3: Become a Validator (Optional)**

**Important Note:** Validator permissions on testnet subnet 428 are **manually granted by the subnet owner** due to the testnet's controlled environment.

#### **Option A: Request Validator Status (Recommended)**

If you want to test validator functionality:

1. **Join our Discord**: [Resi Labs Discord Server](https://discord.gg/resilabs)
2. **Message the team**: Send a DM to `@resi-labs-team` with:
   - Your wallet name and hotkey name
   - Your hotkey address (from the test output)
   - Brief explanation of why you need validator access
3. **Wait for approval**: We'll grant validator permissions within 24 hours
4. **Test validator access**: Use the test script to verify permissions

#### **Option B: Standard Process (May Not Work)**

The standard Bittensor validator process may not work on this testnet:

```bash
# 1. Ensure you have sufficient testnet TAO (typically 100+)
btcli wallet balance --wallet.name YOUR_WALLET --subtensor.network test

# 2. Try to set weights (may fail due to testnet restrictions)
btcli weights commit --subtensor.network test --netuid 428 --wallet.name YOUR_WALLET --wallet.hotkey YOUR_HOTKEY

# 3. Check validator status
python test_testnet_s3_auth.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY --validator-check-only

# Note: This may not work due to testnet configuration
```

#### **Why Manual Approval?**

- **Testnet Environment**: This is a controlled test environment, not open competition
- **Resource Management**: We limit validator slots for testing purposes
- **Quality Control**: We ensure only serious testers get validator access
- **Support**: We can provide better support to approved validators

## 🧪 Testing Workflow

1. **Get Testnet TAO**: Use faucet to get free testnet tokens
2. **Register on Testnet**: Register as miner on subnet 428 testnet
3. **Test API Access**: Run the testnet test script
4. **Request Validator Status** (optional): Contact us on Discord for validator permissions
5. **Test Validator Access**: Once approved, test validator functionality
6. **Move to Production**: Once testnet works, test on subnet 46 mainnet
7. **Begin Mining/Validating**: Start participating with confidence

## 📞 Support

### **For General Issues**

If your testnet test fails after trying the troubleshooting steps:

1. **Include your test output** when asking for help
2. **Specify you're testing on testnet** (subnet 428)
3. **Check the GitHub repository** for known issues
4. **Contact the development team** with specific error messages

### **For Validator Access Requests**

**Discord Contact:**
- **Server**: [Resi Labs Discord](https://discord.gg/resilabs)
- **Channel**: `#testnet-support`
- **Direct Message**: `@resi-labs-team`

**Required Information:**
- Wallet name and hotkey name
- Hotkey address (from test output)
- Brief explanation of testing needs
- Expected timeline for testing

**Response Time:**
- **Validator requests**: Within 24 hours
- **General support**: Within 48 hours
- **Emergency issues**: Use `@urgent` tag in Discord

---

## 🎉 Ready for Production?

**Once your testnet test passes:**

✅ You've verified your wallet setup works  
✅ You understand the authentication flow  
✅ You've tested S3 credential retrieval  
✅ You're ready to test on production (subnet 46)  

**Next Steps:**
1. **Test on Production**: Use `MINER_VALIDATOR_TESTING_GUIDE.md` for subnet 46
2. **Register on Mainnet**: `btcli subnet register --subtensor.network finney --netuid 46`
3. **Start Mining/Validating**: Begin earning real TAO!

## 🛡️ Security Best Practices

### **For Development/Testing:**
- ✅ **Use Standard version** - Convenient and secure enough
- ✅ **Single password prompt** - Good user experience
- ✅ **Wallet caching is safe** - Only public data effectively cached

### **For Production:**
- 🔒 **Use Secure version** - Better security posture
- 🔒 **Address-only caching** - Minimal attack surface
- 🔒 **Wallet reloaded for signing** - Fresh crypto operations

### **For High-Security Environments:**
- 🔐 **Use Maximum Security version** - Zero caching
- 🔐 **Multiple password prompts** - Maximum verification
- 🔐 **Fresh wallet for every operation** - Minimal memory footprint

### **General Security Tips:**
```bash
# Clear command history after testing
history -c

# Use encrypted storage for wallet files
# Consider hardware wallets for high-value operations
# Use VPN for sensitive operations
# Verify API endpoints (HTTPS)
```

**🚀 Testnet success = Production readiness!** 🚀

---

## 📈 **All Security Variants Tested & Working**

✅ **Standard Version**: 1 password prompt, full caching  
✅ **Secure Version**: 2 password prompts, address-only caching  
✅ **Maximum Security**: 3 password prompts, no caching  
✅ **Validator Check**: Works with all variants  
✅ **Bug-Free**: All wallet caching issues resolved  

**Choose your security level and start testing!** 🎯
