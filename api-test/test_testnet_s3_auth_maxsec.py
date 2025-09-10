#!/usr/bin/env python3
"""
MAXIMUM SECURITY VERSION: S3 Auth API Test Script for Testnet Users
No caching - wallet reloaded for every operation

Usage:
    python test_testnet_s3_auth_maxsec.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

Security Level: MAXIMUM
- No caching whatsoever
- Wallet reloaded for every operation
- Password prompted multiple times (2-3x)
- Minimal memory footprint
- Zero persistent wallet references
"""

import time
import requests
import argparse
import sys
from typing import Dict, Any

try:
    import bittensor as bt
except ImportError:
    print("❌ Error: bittensor package not installed")
    sys.exit(1)

# Testnet API Configuration
API_BASE_URL = "https://s3-auth-api-testnet.resilabs.ai"
TESTNET_NETWORK = "test"
TESTNET_SUBNET = 428

class Colors:
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

def get_addresses(wallet_name: str, hotkey_name: str) -> tuple:
    """Load wallet fresh every time - maximum security"""
    print_info("Loading wallet (will prompt for password)...")
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        coldkey = wallet.coldkey.ss58_address
        hotkey = wallet.hotkey.ss58_address
        # Wallet goes out of scope immediately
        return coldkey, hotkey
    except Exception as e:
        print_error(f"Failed to load wallet: {e}")
        return None, None

def sign_message(wallet_name: str, hotkey_name: str, message: str) -> str:
    """Load wallet fresh for signing - maximum security"""
    print_info("Loading wallet for signing (will prompt for password)...")
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        signature = wallet.hotkey.sign(message).hex()
        # Wallet goes out of scope immediately
        return signature
    except Exception as e:
        print_error(f"Failed to sign: {e}")
        return None

def verify_registration(wallet_name: str, hotkey_name: str) -> Dict[str, Any]:
    """Verify registration - loads wallet fresh"""
    print_info("Verifying registration (will prompt for password)...")
    
    try:
        # Fresh wallet load
        _, hotkey_address = get_addresses(wallet_name, hotkey_name)
        if not hotkey_address:
            return {"registered": False}
        
        subtensor = bt.subtensor(network=TESTNET_NETWORK)
        metagraph = subtensor.metagraph(netuid=TESTNET_SUBNET)
        
        if hotkey_address in metagraph.hotkeys:
            idx = metagraph.hotkeys.index(hotkey_address)
            is_validator = bool(metagraph.validator_permit[idx])
            stake = float(metagraph.S[idx])
            
            print_success(f"Hotkey registered!")
            print(f"   Position: {idx}, Validator: {is_validator}, Stake: {stake:.4f}")
            
            return {"registered": True, "is_validator": is_validator}
        else:
            print_error("Hotkey NOT registered")
            return {"registered": False}
            
    except Exception as e:
        print_error(f"Registration check failed: {e}")
        return {"registered": False}

def test_miner_access(wallet_name: str, hotkey_name: str) -> bool:
    """Test miner access - loads wallet fresh for addresses and signing"""
    print_info("Testing miner access...")
    
    try:
        # Fresh load for addresses
        coldkey, hotkey = get_addresses(wallet_name, hotkey_name)
        if not coldkey or not hotkey:
            return False
        
        timestamp = int(time.time())
        commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
        
        # Fresh load for signing
        signature = sign_message(wallet_name, hotkey_name, commitment)
        if not signature:
            return False
        
        # API request
        response = requests.post(f"{API_BASE_URL}/get-folder-access", json={
            "coldkey": coldkey,
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }, timeout=30)
        
        if response.status_code == 200:
            print_success("Miner access granted! 🎉")
            return True
        else:
            print_error(f"Access denied: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="MAXIMUM SECURITY testnet test - no caching")
    parser.add_argument("--wallet", required=True, help="Wallet name")
    parser.add_argument("--hotkey", required=True, help="Hotkey name")
    
    args = parser.parse_args()
    
    print_header("MAXIMUM SECURITY S3 Auth Test")
    print_warning("MAX SECURITY: No caching, wallet reloaded for every operation")
    print_warning("You will be prompted for password multiple times (2-3x)")
    
    # Test registration
    print_header("Step 1: Registration Check")
    reg_info = verify_registration(args.wallet, args.hotkey)
    if not reg_info.get("registered"):
        print_error("Registration required first")
        sys.exit(1)
    
    # Test access
    print_header("Step 2: Access Test")
    success = test_miner_access(args.wallet, args.hotkey)
    
    # Results
    print_header("Results")
    if success:
        print_success("🎉 SUCCESS! Maximum security test passed")
        print_info("Security: Zero caching, wallet reloaded for every operation")
    else:
        print_error("❌ FAILED!")

if __name__ == "__main__":
    main()
