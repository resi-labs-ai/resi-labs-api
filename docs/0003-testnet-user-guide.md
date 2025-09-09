# Mainnet User Guide: Testing S3 API Access

**Document ID**: 0003  
**Title**: Mainnet User Guide for Miners and Validators  
**Author**: Resi Labs Development Team  
**Date**: December 2024  
**Status**: Active  
**Target Audience**: Subnet 46 Miners and Validators on Mainnet

## 🎯 Purpose

This guide helps miners and validators on **mainnet** test their ability to authenticate with the S3 Storage API and receive valid S3 credentials. Use this guide to verify your setup is working correctly and you're ready to participate in subnet 46.

## ⚠️ Important Notes

- **This is for MAINNET** - Use your production wallets registered on finney
- **API Endpoint**: `https://s3-auth-api.resilabs.ai`
- **Network**: Bittensor Finney (Mainnet)
- **Subnet**: 46 (Resi Labs)
- **Purpose**: Validate your production setup and get real S3 access credentials

## 📋 Prerequisites

### 1. Mainnet Wallet Requirements

You need a Bittensor wallet registered on **mainnet subnet 46**:

- **For Miners**: Any registered hotkey on subnet 46
- **For Validators**: Registered hotkey with validator permissions and sufficient stake (typically 1000+ TAO)

### 2. System Requirements

- Python 3.8+
- `bittensor` package installed
- `requests` package for API calls
- Your testnet wallet files accessible

### 3. Verify Your Registration

Before testing, confirm your wallet is registered:

```bash
# Check subnet 46 on mainnet
btcli subnet list --subtensor.network finney | grep -A3 -B3 "46\|Resi"

# Verify your hotkey is registered
btcli subnet metagraph --subtensor.network finney --netuid 46

# Look for your hotkey address in the output
```

## 🚀 Quick Test Script

Download and run this simple test script to validate your setup:

### Step 1: Download the Test Script

Save this as `test_s3_auth.py`:

```python
#!/usr/bin/env python3
"""
S3 Auth API Test Script for Testnet Users
Tests miner and validator authentication with the S3 Storage API
"""

import time
import json
import requests
import argparse
import sys
from typing import Optional, Dict, Any

try:
    import bittensor as bt
except ImportError:
    print("❌ Error: bittensor package not installed")
    print("Install with: pip install bittensor")
    sys.exit(1)

# API Configuration
API_BASE_URL = "https://s3-auth-api.resilabs.ai"
MAINNET_NETWORK = "finney"
MAINNET_SUBNET = 46

class Colors:
    """Terminal colors for better output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def check_api_health() -> bool:
    """Check if the API is accessible and healthy"""
    print_info("Checking API health...")
    try:
        response = requests.get(f"{API_BASE_URL}/healthcheck", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is healthy!")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   S3 OK: {data.get('s3_ok', 'unknown')}")
            print(f"   Bucket: {data.get('bucket', 'unknown')}")
            return True
        else:
            print_error(f"API health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to API: {e}")
        print_warning("Make sure the testnet API is running and accessible")
        return False

def load_wallet(wallet_name: str, hotkey_name: str) -> Optional[bt.wallet]:
    """Load and validate a Bittensor wallet"""
    print_info(f"Loading wallet: {wallet_name}, hotkey: {hotkey_name}")
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        
        # Verify wallet can be accessed
        coldkey_address = wallet.coldkey.ss58_address
        hotkey_address = wallet.hotkey.ss58_address
        
        print_success("Wallet loaded successfully!")
        print(f"   Coldkey: {coldkey_address}")
        print(f"   Hotkey: {hotkey_address}")
        
        return wallet
    except Exception as e:
        print_error(f"Failed to load wallet: {e}")
        print_warning("Make sure your wallet files exist and are accessible")
        return None

def verify_registration(hotkey_address: str) -> Dict[str, Any]:
    """Verify hotkey is registered on mainnet subnet 46"""
    print_info(f"Verifying registration for hotkey: {hotkey_address}")
    
    try:
        subtensor = bt.subtensor(network=MAINNET_NETWORK)
        metagraph = subtensor.metagraph(netuid=MAINNET_SUBNET)
        
        if hotkey_address in metagraph.hotkeys:
            idx = metagraph.hotkeys.index(hotkey_address)
            is_validator = bool(metagraph.validator_permit[idx])
            stake = float(metagraph.S[idx])
            
            print_success(f"Hotkey is registered!")
            print(f"   Position: {idx}")
            print(f"   Is Validator: {is_validator}")
            print(f"   Stake: {stake:.4f}")
            
            return {
                "registered": True,
                "is_validator": is_validator,
                "stake": stake,
                "position": idx
            }
        else:
            print_error("Hotkey is NOT registered on mainnet subnet 46")
            print_warning("Register your hotkey before testing the API")
            return {"registered": False}
            
    except Exception as e:
        print_error(f"Failed to verify registration: {e}")
        return {"registered": False, "error": str(e)}

def test_miner_access(wallet: bt.wallet) -> bool:
    """Test miner access to S3 storage"""
    print_info("Testing miner access...")
    
    try:
        coldkey = wallet.coldkey.ss58_address
        hotkey = wallet.hotkey.ss58_address
        timestamp = int(time.time())
        
        # Create commitment string
        commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        signature = wallet.hotkey.sign(commitment).hex()
        print(f"   Signature: {signature[:32]}...")
        
        # Prepare request
        request_data = {
            "coldkey": coldkey,
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }
        
        # Make API request
        print_info("Making API request...")
        response = requests.post(
            f"{API_BASE_URL}/get-folder-access",
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Miner access granted! 🎉")
            print(f"   Your S3 folder: {data.get('folder', 'N/A')}")
            print(f"   Upload URL: {data.get('url', 'N/A')}")
            print(f"   Access expires: {data.get('expiry', 'N/A')}")
            
            # Show upload fields
            fields = data.get('fields', {})
            if fields:
                print("   Upload fields received:")
                for key, value in fields.items():
                    print(f"     {key}: {str(value)[:50]}...")
            
            return True
        else:
            print_error(f"Miner access denied: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Miner access test failed: {e}")
        return False

def test_validator_access(wallet: bt.wallet) -> bool:
    """Test validator access to S3 storage"""
    print_info("Testing validator access...")
    
    try:
        hotkey = wallet.hotkey.ss58_address
        timestamp = int(time.time())
        
        # Create commitment string
        commitment = f"s3:validator:access:{timestamp}"
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        signature = wallet.hotkey.sign(commitment).hex()
        print(f"   Signature: {signature[:32]}...")
        
        # Prepare request
        request_data = {
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }
        
        # Make API request
        print_info("Making API request...")
        response = requests.post(
            f"{API_BASE_URL}/get-validator-access",
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Validator access granted! 🎉")
            print(f"   Bucket: {data.get('bucket', 'N/A')}")
            print(f"   Region: {data.get('region', 'N/A')}")
            print(f"   Access expires: {data.get('expiry', 'N/A')}")
            
            # Show available URLs
            urls = data.get('urls', {})
            global_urls = urls.get('global', {})
            miner_urls = urls.get('miners', {})
            
            print(f"   Global access URLs: {len(global_urls)}")
            print(f"   Miner access URLs: {len(miner_urls)}")
            
            return True
        else:
            print_error(f"Validator access denied: HTTP {response.status_code}")
            try:
                error_data = response.json()
                error_detail = error_data.get('detail', 'Unknown error')
                print(f"   Error: {error_detail}")
                
                if "not validator" in error_detail.lower():
                    print_warning("Your hotkey doesn't have validator permissions")
                    print_warning("You can still test as a miner")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Validator access test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Test S3 Auth API access for testnet miners and validators"
    )
    parser.add_argument("--wallet", required=True, help="Wallet name")
    parser.add_argument("--hotkey", required=True, help="Hotkey name")
    parser.add_argument("--skip-health", action="store_true", help="Skip API health check")
    
    args = parser.parse_args()
    
    print_header("S3 Auth API Mainnet Test")
    print(f"Testing wallet: {args.wallet}")
    print(f"Testing hotkey: {args.hotkey}")
    print(f"Target API: {API_BASE_URL}")
    print(f"Network: {MAINNET_NETWORK}")
    print(f"Subnet: {MAINNET_SUBNET}")
    
    # Step 1: Check API health
    if not args.skip_health:
        print_header("Step 1: API Health Check")
        if not check_api_health():
            print_error("Cannot proceed - API is not accessible")
            sys.exit(1)
    
    # Step 2: Load wallet
    print_header("Step 2: Wallet Loading")
    wallet = load_wallet(args.wallet, args.hotkey)
    if not wallet:
        print_error("Cannot proceed - wallet loading failed")
        sys.exit(1)
    
    # Step 3: Verify registration
    print_header("Step 3: Registration Verification")
    reg_info = verify_registration(wallet.hotkey.ss58_address)
    if not reg_info.get("registered", False):
        print_error("Cannot proceed - hotkey not registered")
        sys.exit(1)
    
    # Step 4: Test appropriate access
    is_validator = reg_info.get("is_validator", False)
    
    if is_validator:
        print_header("Step 4: Validator Access Test")
        validator_success = test_validator_access(wallet)
        
        print_header("Step 5: Miner Access Test (Validators can also mine)")
        miner_success = test_miner_access(wallet)
        
        overall_success = validator_success or miner_success
    else:
        print_header("Step 4: Miner Access Test")
        overall_success = test_miner_access(wallet)
    
    # Final results
    print_header("Test Results")
    if overall_success:
        print_success("🎉 SUCCESS! Your wallet can authenticate with the S3 API")
        print_success("You're ready for mainnet launch!")
    else:
        print_error("❌ FAILED! Your wallet cannot authenticate with the S3 API")
        print_warning("Please check your setup and try again")
        print_warning("Contact support or check documentation for help")
    
    print("\n" + "="*60)
    print("Test completed.")
    print("="*60)

if __name__ == "__main__":
    main()
```

### Step 2: Run the Test

```bash
# Install required packages if not already installed
pip install bittensor requests

# Run the test script
python test_s3_auth.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

# Example:
python test_s3_auth.py --wallet my_testnet_wallet --hotkey my_testnet_hotkey
```

## 📊 What to Expect

### ✅ Successful Miner Test

```
============================================================
                    S3 Auth API Mainnet Test              
============================================================

============================================================
                     Step 1: API Health Check             
============================================================

ℹ️  Checking API health...
✅ API is healthy!
   Status: ok
   S3 OK: True
   Bucket: 1000-resilabs-caleb-dev-bittensor-sn46-datacollection

============================================================
                     Step 2: Wallet Loading               
============================================================

ℹ️  Loading wallet: my_mainnet_wallet, hotkey: my_mainnet_hotkey
✅ Wallet loaded successfully!
   Coldkey: 5ABC123...XYZ789
   Hotkey: 5DEF456...ABC123

============================================================
                  Step 3: Registration Verification       
============================================================

ℹ️  Verifying registration for hotkey: 5DEF456...ABC123
✅ Hotkey is registered!
   Position: 15
   Is Validator: False
   Stake: 100.5000

============================================================
                    Step 4: Miner Access Test             
============================================================

ℹ️  Testing miner access...
   Commitment: s3:data:access:5ABC123...XYZ789:5DEF456...ABC123:1703123456
   Signature: fc27f1a06424f777...
ℹ️  Making API request...
✅ Miner access granted! 🎉
   Your S3 folder: data/hotkey=5DEF456...ABC123/
   Upload URL: https://1000-resilabs-caleb-dev-bittensor-sn46-datacollection.s3.us-east-2.amazonaws.com
   Access expires: 2024-12-26T15:30:00
   Upload fields received:
     key: data/hotkey=5DEF456...ABC123/${filename}
     AWSAccessKeyId: AKIA...
     policy: eyJ...
     signature: abc123...

============================================================
                         Test Results                     
============================================================

✅ 🎉 SUCCESS! Your wallet can authenticate with the S3 API
✅ You're ready for mainnet launch!

============================================================
Test completed.
============================================================
```

### ✅ Successful Validator Test

```
============================================================
                    Step 4: Validator Access Test         
============================================================

ℹ️  Testing validator access...
   Commitment: s3:validator:access:1703123456
   Signature: 0c6e50361d5c65ad...
ℹ️  Making API request...
✅ Validator access granted! 🎉
   Bucket: 1000-resilabs-caleb-dev-bittensor-sn46-datacollection
   Region: us-east-2
   Access expires: 2024-12-26T15:30:00
   Global access URLs: 1
   Miner access URLs: 1

============================================================
               Step 5: Miner Access Test (Validators can also mine)
============================================================

✅ Miner access granted! 🎉
   [... miner details ...]
```

### ❌ Common Error Scenarios

#### Not Registered
```
❌ Hotkey is NOT registered on mainnet subnet 46
⚠️  Register your hotkey before testing the API
```

#### Not a Validator
```
❌ Validator access denied: HTTP 401
   Error: You are not validator
⚠️  Your hotkey doesn't have validator permissions
⚠️  You can still test as a miner
```

#### API Connection Issues
```
❌ Cannot connect to API: Connection refused
⚠️  Make sure the testnet API is running and accessible
```

## 🔧 Troubleshooting

### Problem: "Cannot connect to API"
**Solutions:**
1. Check if the API URL is correct: `https://s3-auth-api.resilabs.ai`
2. Verify your internet connection
3. Try again later (API might be temporarily down)

### Problem: "Wallet loading failed"
**Solutions:**
1. Verify wallet name and hotkey name are correct
2. Check wallet files exist in `~/.bittensor/wallets/`
3. Ensure wallet password is correct

### Problem: "Hotkey not registered"
**Solutions:**
1. Register your hotkey on mainnet subnet 46:
   ```bash
   btcli subnet register --subtensor.network finney --netuid 46 --wallet.name YOUR_WALLET --wallet.hotkey YOUR_HOTKEY
   ```
2. Wait for registration to be confirmed
3. Verify registration with metagraph command

### Problem: "Invalid signature"
**Solutions:**
1. This usually indicates a server-side issue
2. Try running the test again
3. Report the issue if it persists

## 📝 What This Test Validates

✅ **Wallet Accessibility**: Your wallet files are readable and accessible  
✅ **Network Registration**: Your hotkey is registered on testnet subnet 428  
✅ **Signature Generation**: Your wallet can generate valid signatures  
✅ **API Authentication**: The API accepts your signatures and grants access  
✅ **S3 Credentials**: You receive valid S3 upload/access credentials  
✅ **Validator Permissions**: (If applicable) Your hotkey has validator rights  

## 🎯 Next Steps

Once your test passes:

1. **Save Your Results**: Keep the successful test output for reference
2. **Join Community**: Connect with other miners/validators in Discord
3. **Stay Updated**: Watch for mainnet launch announcements
4. **Prepare Infrastructure**: Set up your mining/validation infrastructure
5. **Monitor Testnet**: Continue testing periodically to ensure continued access

## 📞 Support

If you encounter issues:

1. **Re-run the test** with `--skip-health` flag if API is temporarily down
2. **Check Discord** for known issues and community support
3. **Report persistent issues** to the development team
4. **Include test output** when reporting problems

## 🚨 Security Reminders

- **Use production wallets carefully** - These are real mainnet wallets with real TAO
- **Keep wallet files secure** - Don't share or expose wallet files
- **Monitor transactions** - Verify expected TAO amounts are being used
- **Test with small amounts first** - Start with minimal stake if possible

---

**Ready to test?** Run the script and validate your setup! 🚀
