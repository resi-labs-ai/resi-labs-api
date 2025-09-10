# 🚀 Subnet 46 S3 API Testing Guide for Miners & Validators

**Ready to participate in Bittensor Subnet 46?** Use this guide to test your wallet authentication and verify you can access the S3 storage system.

## ⚡ Quick Start (2 Minutes)

### **Standard Testing (Recommended for Development)**
```bash
# 1. Download the test script
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_mainnet_s3_auth.py

# 2. Create Virtual Environment if Python and Pip are not global
python -m venv venv
source venv/bin/activate

# 3. Install requirements
pip install bittensor requests

# 4. Test your setup (you'll be prompted for password only once)
python test_mainnet_s3_auth.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

# Optional: Check validator status only
python test_mainnet_s3_auth.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME --validator-check-only
```

### **🔒 Security Variants for Production**
Choose based on your security requirements:

```bash
# STANDARD (1 password prompt) - Good for development/testing
python test_mainnet_s3_auth.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY

# SECURE (2 password prompts) - Recommended for production
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_mainnet_s3_auth_secure.py
python test_mainnet_s3_auth_secure.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY

# MAXIMUM SECURITY (3 password prompts) - High-security environments
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_mainnet_s3_auth_maxsec.py
python test_mainnet_s3_auth_maxsec.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY
```

## 📋 What You Need

- **Registered Hotkey**: Your hotkey must be registered on **mainnet subnet 46**
- **Python 3.8+** with `bittensor` and `requests` packages
- **Wallet Access**: Your wallet files and password (if encrypted)

### For Validators
- **Validator Permissions**: Sufficient stake (typically 1000+ TAO) and validator permit
- **Additional Access**: Validators get read access to all miner data

### For Miners  
- **Any Registration**: Any registered hotkey on subnet 46 can mine
- **Upload Access**: You'll get credentials to upload data to your dedicated folder

## ✅ Expected Success Output

When your test passes, you'll see:

```
============================================================
                    S3 Auth API Mainnet Test              
============================================================

✅ API is healthy!
✅ Wallet loaded successfully!
✅ Hotkey is registered! (Position: 15, Stake: 100.5000 TAO)
✅ Miner access granted! 🎉
   Your S3 folder: data/hotkey=5DEF456...ABC123/
   Upload URL: https://bucket.s3.us-east-2.amazonaws.com
   Access expires: 2024-12-26T15:30:00

✅ 🎉 SUCCESS! Your wallet can authenticate with the S3 API
✅ You're ready to participate in subnet 46!
```

## 🔧 Quick Troubleshooting

### ❌ "Hotkey not registered"
```bash
# Register on subnet 46
btcli subnet register --subtensor.network finney --netuid 46 --wallet.name YOUR_WALLET --wallet.hotkey YOUR_HOTKEY

# Verify registration
btcli subnet metagraph --subtensor.network finney --netuid 46
```

### ❌ "Cannot connect to API"
- Check internet connection
- Try again later (API might be temporarily down)
- Run with `--skip-health` to bypass health check

### ❌ "Wallet loading failed"
- Verify wallet name and hotkey name: `btcli wallets list`
- Check wallet files exist: `ls ~/.bittensor/wallets/`
- Ensure correct wallet password

### ❌ "You are not validator"
- Your hotkey is registered as a miner, not validator
- You can still mine! The test will check miner access instead
- To become a validator, you need sufficient stake and validator permissions

### ❌ "Am I a validator?"
```bash
# Check your validator status (works with all security variants)
python test_mainnet_s3_auth.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY --validator-check-only
python test_mainnet_s3_auth_secure.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY --validator-check-only
python test_mainnet_s3_auth_maxsec.py --wallet YOUR_WALLET --hotkey YOUR_HOTKEY --validator-check-only

# Or check manually
btcli subnet metagraph --subtensor.network finney --netuid 46
```

### ❌ "Which security level should I use?"
- **Development/Testing**: Use **Standard** version (1 password, most convenient)
- **Production Scripts**: Use **Secure** version (2 passwords, good balance)
- **High-Security**: Use **Max Security** version (3 passwords, zero caching)
- **All versions tested and working** ✅

## 🎯 What This Test Validates

✅ **Wallet Setup**: Your wallet files work correctly  
✅ **Network Registration**: You're registered on subnet 46  
✅ **API Authentication**: You can authenticate with the S3 API  
✅ **S3 Credentials**: You receive valid upload/access credentials  
✅ **Permissions**: Confirms your miner/validator status  

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

## 📊 API Information

- **Live API**: `https://s3-auth-api.resilabs.ai`
- **Network**: Bittensor Finney (Mainnet)
- **Subnet**: 46 (Resi Labs)
- **Bucket Structure**: `data/hotkey={your_hotkey}/job_id={job_id}/`

## 🔗 Additional Resources

- **Full Documentation**: [GitHub Repository](https://github.com/resi-labs-ai/resi-labs-api)
- **API Health**: [https://s3-auth-api.resilabs.ai/healthcheck](https://s3-auth-api.resilabs.ai/healthcheck)
- **API Docs**: [https://s3-auth-api.resilabs.ai/docs](https://s3-auth-api.resilabs.ai/docs)
- **Testnet Guide**: `TESTNET_MINER_VALIDATOR_TESTING_GUIDE.md`

### **📥 Download Security Variants:**
```bash
# Standard version (already included in repo)
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_mainnet_s3_auth.py

# Secure version
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_mainnet_s3_auth_secure.py

# Maximum security version
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/test_mainnet_s3_auth_maxsec.py

# Security comparison tool
curl -O https://raw.githubusercontent.com/resi-labs-ai/resi-labs-api/main/api-test/security_comparison.py
python security_comparison.py  # View comparison table
```

## 📞 Support

If your test fails after trying the troubleshooting steps:

1. **Include your test output** when asking for help
2. **Check the GitHub repository** for known issues
3. **Contact the development team** with specific error messages

---

**🎉 Once your test passes, you're ready to participate in Subnet 46!**

The test confirms you can:
- ✅ Authenticate with the S3 API
- ✅ Receive valid storage credentials  
- ✅ Upload data (miners) or access all data (validators)

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

**Start mining or validating with confidence!** 🚀

---

## 📈 **All Security Variants Tested & Working**

✅ **Standard Version**: 1 password prompt, full caching  
✅ **Secure Version**: 2 password prompts, address-only caching  
✅ **Maximum Security**: 3 password prompts, no caching  
✅ **Validator Check**: Works with all variants  
✅ **Production Ready**: All variants tested on mainnet  

**Choose your security level and start participating!** 🎯
