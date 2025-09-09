#!/usr/bin/env python3
"""
S3 Auth API Test Script for Mainnet Users
Tests miner and validator authentication with the S3 Storage API

Usage:
    python test_mainnet_s3_auth.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

Requirements:
    pip install bittensor requests

Author: Resi Labs Development Team
Network: Bittensor Finney (Mainnet)
Subnet: 46 (Resi Labs)
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
        print_warning("Make sure the API is running and accessible")
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
            print(f"   Stake: {stake:.4f} TAO")
            
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
            
            # Show structure info
            structure_info = data.get('structure_info', {})
            if structure_info:
                print(f"   Folder structure: {structure_info.get('folder_structure', 'N/A')}")
            
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
            
            # Show structure info
            structure_info = data.get('structure_info', {})
            if structure_info:
                print(f"   Folder structure: {structure_info.get('folder_structure', 'N/A')}")
            
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
        description="Test S3 Auth API access for mainnet miners and validators",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_mainnet_s3_auth.py --wallet my_wallet --hotkey my_hotkey
  python test_mainnet_s3_auth.py --wallet validator_wallet --hotkey validator_hotkey --skip-health

Network: Bittensor Finney (Mainnet)
Subnet: 46 (Resi Labs)
API: https://s3-auth-api.resilabs.ai
        """
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
            print_info("You can try running with --skip-health to bypass this check")
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
        print_info("Register with: btcli subnet register --subtensor.network finney --netuid 46")
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
        print_success("You're ready to participate in subnet 46!")
        print_info("Next steps:")
        print_info("1. Set up your mining/validation infrastructure")
        print_info("2. Monitor the subnet for activity")
        print_info("3. Start uploading data (miners) or accessing data (validators)")
    else:
        print_error("❌ FAILED! Your wallet cannot authenticate with the S3 API")
        print_warning("Please check your setup and try again")
        print_warning("Common issues:")
        print_warning("- Wallet not registered on subnet 46")
        print_warning("- Network connectivity problems")
        print_warning("- API temporarily unavailable")
    
    print("\n" + "="*60)
    print("Test completed.")
    print("For support, check the documentation or contact the development team.")
    print("="*60)

if __name__ == "__main__":
    main()
