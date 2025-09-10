#!/usr/bin/env python3
"""
MAXIMUM SECURITY VERSION: S3 Auth API Test Script for Production Users
No caching - wallet reloaded for every operation

Usage:
    python test_mainnet_s3_auth_maxsec.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME

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

# Production API Configuration
API_BASE_URL = "https://s3-auth-api.resilabs.ai"
MAINNET_NETWORK = "finney"
MAINNET_SUBNET = 46

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

def check_api_health() -> bool:
    """Check if the production API is accessible and healthy"""
    print_info("Checking production API health...")
    try:
        response = requests.get(f"{API_BASE_URL}/healthcheck", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Production API is healthy!")
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Production API health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to production API: {e}")
        return False

def verify_registration(wallet_name: str, hotkey_name: str) -> Dict[str, Any]:
    """Verify registration - loads wallet fresh"""
    print_info("Verifying registration (will prompt for password)...")
    
    try:
        # Fresh wallet load
        _, hotkey_address = get_addresses(wallet_name, hotkey_name)
        if not hotkey_address:
            return {"registered": False}
        
        subtensor = bt.subtensor(network=MAINNET_NETWORK)
        metagraph = subtensor.metagraph(netuid=MAINNET_SUBNET)
        
        if hotkey_address in metagraph.hotkeys:
            idx = metagraph.hotkeys.index(hotkey_address)
            is_validator = bool(metagraph.validator_permit[idx])
            stake = float(metagraph.S[idx])
            
            print_success(f"Hotkey registered on mainnet!")
            print(f"   Position: {idx}, Validator: {is_validator}, Stake: {stake:.4f} TAO")
            
            return {"registered": True, "is_validator": is_validator}
        else:
            print_error("Hotkey NOT registered on mainnet")
            return {"registered": False}
            
    except Exception as e:
        print_error(f"Registration check failed: {e}")
        return {"registered": False}

def test_miner_access(wallet_name: str, hotkey_name: str) -> bool:
    """Test miner access - loads wallet fresh for addresses and signing"""
    print_info("Testing production miner access...")
    
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
            data = response.json()
            print_success("Production miner access granted! 🎉")
            print(f"   Your S3 folder: {data.get('folder', 'N/A')}")
            print(f"   Upload URL: {data.get('url', 'N/A')}")
            print(f"   Access expires: {data.get('expiry', 'N/A')}")
            return True
        else:
            print_error(f"Production miner access denied: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Production miner test failed: {e}")
        return False

def test_validator_access(wallet_name: str, hotkey_name: str) -> bool:
    """Test validator access - loads wallet fresh for addresses and signing"""
    print_info("Testing production validator access...")
    
    try:
        # Fresh load for addresses
        _, hotkey = get_addresses(wallet_name, hotkey_name)
        if not hotkey:
            return False
        
        timestamp = int(time.time())
        commitment = f"s3:validator:access:{timestamp}"
        
        # Fresh load for signing
        signature = sign_message(wallet_name, hotkey_name, commitment)
        if not signature:
            return False
        
        # API request
        response = requests.post(f"{API_BASE_URL}/get-validator-access", json={
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }, timeout=30)
        
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
            print_error(f"Production validator access denied: {response.status_code}")
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
        print_error(f"Production validator test failed: {e}")
        return False

def check_validator_status(wallet_name: str, hotkey_name: str) -> bool:
    """Standalone validator status checker"""
    print_header("Validator Status Check")
    print_info("This will check if your hotkey is registered as a validator on mainnet")
    
    try:
        _, hotkey_address = get_addresses(wallet_name, hotkey_name)
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
        description="MAXIMUM SECURITY production test - no caching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_mainnet_s3_auth_maxsec.py --wallet my_wallet --hotkey my_hotkey
  python test_mainnet_s3_auth_maxsec.py --wallet validator_wallet --hotkey validator_hotkey --validator-check-only

Network: Bittensor Finney (Mainnet)
Subnet: 46 (Resi Labs)
API: https://s3-auth-api.resilabs.ai

Security: Maximum - No caching, wallet reloaded for every operation
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
    
    print_header("MAXIMUM SECURITY S3 Auth Production Test")
    print_warning("MAX SECURITY: No caching, wallet reloaded for every operation")
    print_warning("You will be prompted for password multiple times (2-3x)")
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
    
    # Step 2: Test registration
    print_header("Step 2: Registration Check")
    reg_info = verify_registration(args.wallet, args.hotkey)
    if not reg_info.get("registered"):
        print_error("Registration required first")
        print_info("Register with: btcli subnet register --subtensor.network finney --netuid 46")
        sys.exit(1)
    
    # Step 3: Test appropriate access
    is_validator = reg_info.get("is_validator", False)
    
    if is_validator:
        print_header("Step 3: Production Validator Access Test")
        validator_success = test_validator_access(args.wallet, args.hotkey)
        
        print_header("Step 4: Production Miner Access Test (Validators can also mine)")
        miner_success = test_miner_access(args.wallet, args.hotkey)
        
        overall_success = validator_success or miner_success
    else:
        print_header("Step 3: Production Miner Access Test")
        overall_success = test_miner_access(args.wallet, args.hotkey)
    
    # Results
    print_header("Production Test Results")
    if overall_success:
        print_success("🎉 SUCCESS! Maximum security production test passed")
        print_success("You're ready to participate in subnet 46!")
        print_info("Security: Zero caching, wallet reloaded for every operation")
        print_info("Next steps:")
        print_info("1. Set up your mining/validation infrastructure")
        print_info("2. Monitor the subnet for activity")
        print_info("3. Start uploading data (miners) or accessing data (validators)")
    else:
        print_error("❌ FAILED! Production access test unsuccessful")
        print_warning("Please check your setup and try again")

if __name__ == "__main__":
    main()
