#!/usr/bin/env python3
"""
SECURE VERSION: S3 Auth API Test Script for Testnet Users
Only caches public addresses, re-prompts for signing operations

Usage:
    python test_testnet_s3_auth_secure.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

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

# Testnet API Configuration
API_BASE_URL = "https://s3-auth-api-testnet.resilabs.ai"
TESTNET_NETWORK = "test"
TESTNET_SUBNET = 428

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
    """Check if the testnet API is accessible and healthy"""
    print_info("Checking testnet API health...")
    try:
        response = requests.get(f"{API_BASE_URL}/healthcheck", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Testnet API is healthy!")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   S3 OK: {data.get('s3_ok', 'unknown')}")
            print(f"   Bucket: {data.get('bucket', 'unknown')}")
            return True
        else:
            print_error(f"Testnet API health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to testnet API: {e}")
        return False

def verify_registration(hotkey_address: str) -> Dict[str, Any]:
    """Verify hotkey is registered on testnet subnet 428"""
    print_info(f"Verifying registration for hotkey: {hotkey_address}")
    
    try:
        subtensor = bt.subtensor(network=TESTNET_NETWORK)
        metagraph = subtensor.metagraph(netuid=TESTNET_SUBNET)
        
        if hotkey_address in metagraph.hotkeys:
            idx = metagraph.hotkeys.index(hotkey_address)
            is_validator = bool(metagraph.validator_permit[idx])
            stake = float(metagraph.S[idx])
            
            print_success(f"Hotkey is registered on testnet!")
            print(f"   Position: {idx}")
            print(f"   Is Validator: {is_validator}")
            print(f"   Stake: {stake:.4f} testnet TAO")
            
            return {
                "registered": True,
                "is_validator": is_validator,
                "stake": stake,
                "position": idx
            }
        else:
            print_error("Hotkey is NOT registered on testnet subnet 428")
            return {"registered": False}
            
    except Exception as e:
        print_error(f"Failed to verify registration: {e}")
        return {"registered": False, "error": str(e)}

def test_miner_access(wallet_name: str, hotkey_name: str) -> bool:
    """Test miner access to testnet S3 storage"""
    print_info("Testing testnet miner access...")
    
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
        
        print_info("Making testnet API request...")
        response = requests.post(f"{API_BASE_URL}/get-folder-access", json=request_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Testnet miner access granted! 🎉")
            print(f"   Your S3 folder: {data.get('folder', 'N/A')}")
            print(f"   Upload URL: {data.get('url', 'N/A')}")
            print(f"   Access expires: {data.get('expiry', 'N/A')}")
            return True
        else:
            print_error(f"Testnet miner access denied: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Testnet miner access test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="SECURE testnet S3 API test - minimal caching")
    parser.add_argument("--wallet", required=True, help="Wallet name")
    parser.add_argument("--hotkey", required=True, help="Hotkey name")
    parser.add_argument("--skip-health", action="store_true", help="Skip API health check")
    
    args = parser.parse_args()
    
    print_header("SECURE S3 Auth API Testnet Test")
    print_warning("SECURE MODE: Only caches public addresses, re-prompts for signing")
    print(f"Testing wallet: {args.wallet}")
    print(f"Testing hotkey: {args.hotkey}")
    
    # Step 1: Health check
    if not args.skip_health and not check_api_health():
        sys.exit(1)
    
    # Step 2: Load and cache addresses
    print_header("Step 1: Address Loading")
    coldkey, hotkey = load_and_cache_addresses(args.wallet, args.hotkey)
    if not coldkey or not hotkey:
        sys.exit(1)
    
    # Step 3: Verify registration
    print_header("Step 2: Registration Verification")
    reg_info = verify_registration(hotkey)
    if not reg_info.get("registered", False):
        print_error("Hotkey not registered on testnet")
        sys.exit(1)
    
    # Step 4: Test access
    print_header("Step 3: API Access Test")
    success = test_miner_access(args.wallet, args.hotkey)
    
    # Results
    print_header("Test Results")
    if success:
        print_success("🎉 SUCCESS! Secure testnet access confirmed")
        print_info("Security: Only public addresses cached, wallet reloaded for signing")
    else:
        print_error("❌ FAILED! Access test unsuccessful")

if __name__ == "__main__":
    main()
