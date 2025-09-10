#!/usr/bin/env python3
"""
SECURE VERSION: S3 Auth API Test Script for Production Users
Only caches public addresses, re-prompts for signing operations

Usage:
    python test_mainnet_s3_auth_secure.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

Security Level: HIGH
- Only caches public addresses (already on-chain)
- Wallet object not kept in memory
- Re-prompts for password during signing operations
- Minimal attack surface
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

# Production API Configuration
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

# Secure cache - only stores PUBLIC addresses
_address_cache = {}

def load_and_cache_addresses(wallet_name: str, hotkey_name: str) -> tuple:
    """Load wallet and cache only the PUBLIC addresses"""
    cache_key = f"{wallet_name}:{hotkey_name}"
    
    if cache_key in _address_cache:
        print_info("Using cached addresses (no password needed)")
        return _address_cache[cache_key]['coldkey'], _address_cache[cache_key]['hotkey']
    
    print_info(f"Loading wallet addresses: {wallet_name}, hotkey: {hotkey_name}")
    print_info("You'll be prompted for password to read addresses...")
    
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        coldkey_address = wallet.coldkey.ss58_address
        hotkey_address = wallet.hotkey.ss58_address
        
        # Cache ONLY the public addresses
        _address_cache[cache_key] = {
            'coldkey': coldkey_address,
            'hotkey': hotkey_address
        }
        
        print_success("Addresses cached successfully!")
        print(f"   Coldkey: {coldkey_address}")
        print(f"   Hotkey: {hotkey_address}")
        
        return coldkey_address, hotkey_address
        
    except Exception as e:
        print_error(f"Failed to load wallet: {e}")
        return None, None

def sign_with_wallet(wallet_name: str, hotkey_name: str, message: str) -> str:
    """Load wallet fresh for signing (more secure, may prompt for password)"""
    print_info("Loading wallet for signing (may prompt for password)...")
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        signature = wallet.hotkey.sign(message).hex()
        # Wallet object goes out of scope immediately after signing
        return signature
    except Exception as e:
        print_error(f"Failed to sign message: {e}")
        return None

def check_api_health() -> bool:
    """Check if the production API is accessible and healthy"""
    print_info("Checking production API health...")
    try:
        response = requests.get(f"{API_BASE_URL}/healthcheck", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Production API is healthy!")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   S3 OK: {data.get('s3_ok', 'unknown')}")
            print(f"   Bucket: {data.get('bucket', 'unknown')}")
            return True
        else:
            print_error(f"Production API health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to production API: {e}")
        return False

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
            
            print_success(f"Hotkey is registered on mainnet!")
            print(f"   Position: {idx}")
            print(f"   Is Validator: {is_validator}")
            print(f"   Stake: {stake:.4f} TAO")
            
            return {
                "registered": True,
                "is_validator": is_validator,
                "stake": stake,
                "position": idx
            }
        else:
            print_error("Hotkey is NOT registered on mainnet subnet 46")
            return {"registered": False}
            
    except Exception as e:
        print_error(f"Failed to verify registration: {e}")
        return {"registered": False, "error": str(e)}

def test_miner_access(wallet_name: str, hotkey_name: str) -> bool:
    """Test miner access to production S3 storage"""
    print_info("Testing production miner access...")
    
    try:
        # Use cached addresses
        coldkey, hotkey = load_and_cache_addresses(wallet_name, hotkey_name)
        if not coldkey or not hotkey:
            return False
            
        timestamp = int(time.time())
        commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
        print(f"   Commitment: {commitment}")
        
        # Fresh wallet load for signing (more secure)
        signature = sign_with_wallet(wallet_name, hotkey_name, commitment)
        if not signature:
            return False
            
        print(f"   Signature: {signature[:32]}...")
        
        # Make API request
        request_data = {
            "coldkey": coldkey,
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }
        
        print_info("Making production API request...")
        response = requests.post(f"{API_BASE_URL}/get-folder-access", json=request_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Production miner access granted! 🎉")
            print(f"   Your S3 folder: {data.get('folder', 'N/A')}")
            print(f"   Upload URL: {data.get('url', 'N/A')}")
            print(f"   Access expires: {data.get('expiry', 'N/A')}")
            return True
        else:
            print_error(f"Production miner access denied: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Production miner access test failed: {e}")
        return False

def test_validator_access(wallet_name: str, hotkey_name: str) -> bool:
    """Test validator access to production S3 storage"""
    print_info("Testing production validator access...")
    
    try:
        # Use cached address
        _, hotkey = load_and_cache_addresses(wallet_name, hotkey_name)
        if not hotkey:
            return False
            
        timestamp = int(time.time())
        commitment = f"s3:validator:access:{timestamp}"
        print(f"   Commitment: {commitment}")
        
        # Fresh wallet load for signing (more secure)
        signature = sign_with_wallet(wallet_name, hotkey_name, commitment)
        if not signature:
            return False
            
        print(f"   Signature: {signature[:32]}...")
        
        # Make API request
        request_data = {
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }
        
        print_info("Making production API request...")
        response = requests.post(f"{API_BASE_URL}/get-validator-access", json=request_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Production validator access granted! 🎉")
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
            print_error(f"Production validator access denied: HTTP {response.status_code}")
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
        print_error(f"Production validator access test failed: {e}")
        return False

def check_validator_status(wallet_name: str, hotkey_name: str) -> bool:
    """Standalone validator status checker"""
    print_header("Validator Status Check")
    print_info("This will check if your hotkey is registered as a validator on mainnet")
    
    try:
        _, hotkey_address = load_and_cache_addresses(wallet_name, hotkey_name)
        if not hotkey_address:
            return False
        
        subtensor = bt.subtensor(network=MAINNET_NETWORK)
        metagraph = subtensor.metagraph(netuid=MAINNET_SUBNET)
        
        if hotkey_address in metagraph.hotkeys:
            idx = metagraph.hotkeys.index(hotkey_address)
            is_validator = bool(metagraph.validator_permit[idx])
            stake = float(metagraph.S[idx])
            
            print_success(f"Hotkey is registered on mainnet subnet {MAINNET_SUBNET}!")
            print(f"   Position: {idx}")
            print(f"   Stake: {stake:.4f} TAO")
            
            if is_validator:
                print_success("✅ You ARE a validator!")
                print_info("You can test validator access with the full test script")
            else:
                print_warning("❌ You are NOT a validator (you're a miner)")
                print_info("To become a validator:")
                print_info("  1. Ensure sufficient stake (typically 1000+ TAO)")
                print_info("  2. Run: btcli subnet set_weights --subtensor.network finney --netuid 46")
                print_info("  3. Wait for validator permit to be granted")
            
            return is_validator
        else:
            print_error("Hotkey is NOT registered on mainnet subnet 46")
            print_info("Register first: btcli subnet register --subtensor.network finney --netuid 46")
            return False
            
    except Exception as e:
        print_error(f"Failed to check validator status: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="SECURE production S3 API test - minimal caching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_mainnet_s3_auth_secure.py --wallet my_wallet --hotkey my_hotkey
  python test_mainnet_s3_auth_secure.py --wallet validator_wallet --hotkey validator_hotkey --validator-check-only

Network: Bittensor Finney (Mainnet)
Subnet: 46 (Resi Labs)
API: https://s3-auth-api.resilabs.ai

Security: Only caches public addresses, re-prompts for signing
        """
    )
    parser.add_argument("--wallet", required=True, help="Wallet name")
    parser.add_argument("--hotkey", required=True, help="Hotkey name")
    parser.add_argument("--skip-health", action="store_true", help="Skip API health check")
    parser.add_argument("--validator-check-only", action="store_true", help="Only check validator status and exit")
    
    args = parser.parse_args()
    
    # Handle validator-check-only mode
    if args.validator_check_only:
        check_validator_status(args.wallet, args.hotkey)
        sys.exit(0)
    
    print_header("SECURE S3 Auth API Production Test")
    print_warning("SECURE MODE: Only caches public addresses, re-prompts for signing")
    print(f"Testing wallet: {args.wallet}")
    print(f"Testing hotkey: {args.hotkey}")
    print(f"Target API: {API_BASE_URL}")
    print(f"Network: {MAINNET_NETWORK}")
    print(f"Subnet: {MAINNET_SUBNET}")
    
    # Step 1: Health check
    if not args.skip_health:
        print_header("Step 1: Production API Health Check")
        if not check_api_health():
            print_error("Cannot proceed - production API is not accessible")
            sys.exit(1)
    
    # Step 2: Load and cache addresses
    print_header("Step 2: Address Loading")
    coldkey, hotkey = load_and_cache_addresses(args.wallet, args.hotkey)
    if not coldkey or not hotkey:
        print_error("Cannot proceed - address loading failed")
        sys.exit(1)
    
    # Step 3: Verify registration
    print_header("Step 3: Registration Verification")
    reg_info = verify_registration(hotkey)
    if not reg_info.get("registered", False):
        print_error("Cannot proceed - hotkey not registered on mainnet")
        print_info("Register with: btcli subnet register --subtensor.network finney --netuid 46")
        sys.exit(1)
    
    # Step 4: Test appropriate access
    is_validator = reg_info.get("is_validator", False)
    
    if is_validator:
        print_header("Step 4: Production Validator Access Test")
        validator_success = test_validator_access(args.wallet, args.hotkey)
        
        print_header("Step 5: Production Miner Access Test (Validators can also mine)")
        miner_success = test_miner_access(args.wallet, args.hotkey)
        
        overall_success = validator_success or miner_success
    else:
        print_header("Step 4: Production Miner Access Test")
        overall_success = test_miner_access(args.wallet, args.hotkey)
    
    # Results
    print_header("Production Test Results")
    if overall_success:
        print_success("🎉 SUCCESS! Secure production access confirmed")
        print_success("You're ready to participate in subnet 46!")
        print_info("Security: Only public addresses cached, wallet reloaded for signing")
        print_info("Next steps:")
        print_info("1. Set up your mining/validation infrastructure")
        print_info("2. Monitor the subnet for activity")
        print_info("3. Start uploading data (miners) or accessing data (validators)")
    else:
        print_error("❌ FAILED! Production access test unsuccessful")
        print_warning("Please check your setup and try again")

if __name__ == "__main__":
    main()
