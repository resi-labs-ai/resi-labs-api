#!/usr/bin/env python3
"""
Simple API testing script for S3 Auth API
Usage: python test_api.py --wallet <wallet_name> --hotkey <hotkey_name>
"""

import time
import json
import requests
import argparse
import bittensor as bt

# API Configuration
API_BASE_URL = "https://s3-auth-api.resilabs.ai"
API_IP = "18.116.177.52"  # For DNS resolution

def make_request(endpoint, method="GET", data=None, headers=None):
    """Make HTTP request with DNS resolution"""
    url = f"{API_BASE_URL}{endpoint}"
    
    # Create session with custom DNS resolution
    session = requests.Session()
    session.headers.update({"Host": "s3-auth-api.resilabs.ai"})
    
    # Replace hostname with IP for actual request
    actual_url = url.replace("s3-auth-api.resilabs.ai", API_IP)
    
    if method == "GET":
        response = session.get(actual_url, headers=headers)
    elif method == "POST":
        response = session.post(actual_url, json=data, headers=headers)
    
    return response

def test_healthcheck():
    """Test the healthcheck endpoint"""
    print("🏥 Testing healthcheck endpoint...")
    try:
        response = make_request("/healthcheck")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy!")
            print(f"   Bucket: {data['bucket']}")
            print(f"   Region: {data['region']}")
            print(f"   Folder Structure: {data['folder_structure']}")
            print(f"   S3 OK: {data['s3_ok']}")
            print(f"   Redis OK: {data['redis_ok']}")
            return True
        else:
            print(f"❌ Healthcheck failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Healthcheck error: {e}")
        return False

def test_miner_access(wallet):
    """Test miner folder access endpoint"""
    print("\n⛏️  Testing miner folder access...")
    
    try:
        # Generate timestamp
        timestamp = int(time.time())
        
        # Create commitment message
        coldkey = wallet.coldkey.ss58_address
        hotkey = wallet.hotkey.ss58_address
        commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
        
        print(f"   Coldkey: {coldkey}")
        print(f"   Hotkey: {hotkey}")
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        message_bytes = commitment.encode('utf-8')
        signature = wallet.hotkey.sign(message_bytes)
        signature_hex = "0x" + signature.hex()
        
        # Prepare request data
        request_data = {
            "coldkey": coldkey,
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature_hex
        }
        
        print(f"   Signature: {signature_hex[:20]}...")
        
        # Make API request
        response = make_request("/get-folder-access", method="POST", data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Miner access granted!")
            print(f"   Folder: {data['folder']}")
            print(f"   Upload URL: {data['url']}")
            print(f"   Expires: {data['expiry']}")
            return True
        else:
            print(f"❌ Miner access failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Miner access error: {e}")
        return False

def test_validator_access(wallet):
    """Test validator access endpoint"""
    print("\n🔍 Testing validator access...")
    
    try:
        # Generate timestamp
        timestamp = int(time.time())
        
        # Create commitment message for validator
        hotkey = wallet.hotkey.ss58_address
        commitment = f"s3:validator:access:{timestamp}"
        
        print(f"   Hotkey: {hotkey}")
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        message_bytes = commitment.encode('utf-8')
        signature = wallet.hotkey.sign(message_bytes)
        signature_hex = "0x" + signature.hex()
        
        # Prepare request data
        request_data = {
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature_hex
        }
        
        print(f"   Signature: {signature_hex[:20]}...")
        
        # Make API request
        response = make_request("/get-validator-access", method="POST", data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Validator access granted!")
            print(f"   Bucket: {data['bucket']}")
            print(f"   Validator Hotkey: {data['validator_hotkey']}")
            print(f"   Expires: {data['expiry']}")
            print(f"   URLs available: {len(data['urls']['global'])} global, {len(data['urls']['miners'])} miner")
            return True
        else:
            print(f"❌ Validator access failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Validator access error: {e}")
        return False

def test_miner_specific_access(wallet, miner_hotkey):
    """Test miner-specific access endpoint (validator only)"""
    print(f"\n🎯 Testing miner-specific access for {miner_hotkey[:20]}...")
    
    try:
        # Generate timestamp
        timestamp = int(time.time())
        
        # Create commitment message
        hotkey = wallet.hotkey.ss58_address
        commitment = f"s3:validator:miner:{miner_hotkey}:{timestamp}"
        
        print(f"   Validator Hotkey: {hotkey}")
        print(f"   Target Miner: {miner_hotkey}")
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        message_bytes = commitment.encode('utf-8')
        signature = wallet.hotkey.sign(message_bytes)
        signature_hex = "0x" + signature.hex()
        
        # Prepare request data
        request_data = {
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature_hex,
            "miner_hotkey": miner_hotkey
        }
        
        print(f"   Signature: {signature_hex[:20]}...")
        
        # Make API request
        response = make_request("/get-miner-specific-access", method="POST", data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Miner-specific access granted!")
            print(f"   Bucket: {data['bucket']}")
            print(f"   Miner Hotkey: {data['miner_hotkey']}")
            print(f"   Prefix: {data['prefix']}")
            print(f"   Expires: {data['expiry']}")
            return True
        else:
            print(f"❌ Miner-specific access failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Miner-specific access error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test S3 Auth API endpoints")
    parser.add_argument("--wallet", required=True, help="Wallet name")
    parser.add_argument("--hotkey", required=True, help="Hotkey name")
    parser.add_argument("--test-miner-hotkey", help="Test miner hotkey for validator-specific access")
    parser.add_argument("--skip-validator", action="store_true", help="Skip validator tests")
    parser.add_argument("--dev", action="store_true", help="Use local development server")
    
    args = parser.parse_args()
    
    # Set global flag for dev mode
    global USE_DEV
    USE_DEV = args.dev
    
    print("🚀 S3 Auth API Testing Script")
    print("=" * 50)
    
    # Test healthcheck first
    if not test_healthcheck():
        print("❌ Cannot proceed - API is not healthy")
        return
    
    # Load wallet
    print(f"\n🔑 Loading wallet: {args.wallet} / {args.hotkey}")
    try:
        wallet = bt.wallet(name=args.wallet, hotkey=args.hotkey)
        print(f"   Wallet loaded successfully!")
        print(f"   Coldkey: {wallet.coldkey.ss58_address}")
        print(f"   Hotkey: {wallet.hotkey.ss58_address}")
    except Exception as e:
        print(f"❌ Failed to load wallet: {e}")
        return
    
    # Test miner access
    miner_success = test_miner_access(wallet)
    
    # Test validator access (unless skipped)
    validator_success = False
    if not args.skip_validator:
        validator_success = test_validator_access(wallet)
        
        # Test miner-specific access if we have a test miner hotkey
        if validator_success and args.test_miner_hotkey:
            test_miner_specific_access(wallet, args.test_miner_hotkey)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Healthcheck: ✅ PASS")
    print(f"   Miner Access: {'✅ PASS' if miner_success else '❌ FAIL'}")
    if not args.skip_validator:
        print(f"   Validator Access: {'✅ PASS' if validator_success else '❌ FAIL'}")
    
    if miner_success:
        print(f"\n🎉 Your API is working! Bucket configured: 4000-resilabs-prod-bittensor-sn46-datacollection")
    else:
        print(f"\n⚠️  Some tests failed. Check your wallet configuration and signature verification.")

if __name__ == "__main__":
    main()
