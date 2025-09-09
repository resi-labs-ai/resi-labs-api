#!/usr/bin/env python3
"""
Local API testing script for S3 Auth API
Usage: python test_local.py --wallet <wallet_name> --hotkey <hotkey_name> --type <miner|validator>
"""

import time
import json
import requests
import argparse
import bittensor as bt

# Local API Configuration
API_BASE_URL = "http://localhost:8000"

def make_request(endpoint, method="GET", data=None, headers=None):
    """Make HTTP request to local server"""
    url = f"{API_BASE_URL}{endpoint}"
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, json=data, headers=headers)
    
    return response

def test_healthcheck():
    """Test the healthcheck endpoint"""
    print("🏥 Testing healthcheck endpoint...")
    try:
        response = make_request("/healthcheck")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy!")
            print(f"   Status: {data['status']}")
            print(f"   Bucket: {data['bucket']}")
            print(f"   Region: {data['region']}")
            print(f"   Folder Structure: {data['folder_structure']}")
            print(f"   S3 OK: {data['s3_ok']}")
            print(f"   Redis OK: {data['redis_ok']}")
            print(f"   Metagraph Syncer: {data['metagraph_syncer']['enabled']}")
            return True
        else:
            print(f"❌ Healthcheck failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Healthcheck error: {e}")
        return False

def test_miner_access(wallet_name, hotkey_name):
    """Test miner folder access"""
    print(f"⛏️  Testing miner access for wallet: {wallet_name}, hotkey: {hotkey_name}")
    
    try:
        # Load wallet and keypair
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        coldkey = wallet.coldkey.ss58_address
        hotkey = wallet.hotkey.ss58_address
        
        print(f"   Coldkey: {coldkey}")
        print(f"   Hotkey: {hotkey}")
        
        # Create commitment and signature
        timestamp = int(time.time())
        commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
        
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        signature = wallet.hotkey.sign(commitment).hex()
        
        # Prepare request data
        request_data = {
            "coldkey": coldkey,
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }
        
        print("   Making API request...")
        response = make_request("/get-folder-access", method="POST", data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Miner access granted!")
            print(f"   Folder: {data['folder']}")
            print(f"   Upload URL: {data['url']}")
            print(f"   Expiry: {data['expiry']}")
            print(f"   List URL: {data['list_url']}")
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

def test_validator_access(wallet_name, hotkey_name):
    """Test validator access"""
    print(f"👑 Testing validator access for wallet: {wallet_name}, hotkey: {hotkey_name}")
    
    try:
        # Load wallet and keypair
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        hotkey = wallet.hotkey.ss58_address
        
        print(f"   Hotkey: {hotkey}")
        
        # Create commitment and signature
        timestamp = int(time.time())
        commitment = f"s3:validator:access:{timestamp}"
        
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        signature = wallet.hotkey.sign(commitment).hex()
        
        # Prepare request data
        request_data = {
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature
        }
        
        print("   Making API request...")
        response = make_request("/get-validator-access", method="POST", data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Validator access granted!")
            print(f"   Validator Hotkey: {data['validator_hotkey']}")
            print(f"   Bucket: {data['bucket']}")
            print(f"   Region: {data['region']}")
            print(f"   Expiry: {data['expiry']}")
            print(f"   Global URLs available: {len(data['urls']['global'])}")
            print(f"   Miner URLs available: {len(data['urls']['miners'])}")
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

def test_miner_specific_access(wallet_name, hotkey_name, miner_hotkey):
    """Test validator access to specific miner data"""
    print(f"🔍 Testing validator access to miner data for wallet: {wallet_name}, hotkey: {hotkey_name}")
    print(f"   Target miner hotkey: {miner_hotkey}")
    
    try:
        # Load wallet and keypair
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        hotkey = wallet.hotkey.ss58_address
        
        # Create commitment and signature
        timestamp = int(time.time())
        commitment = f"s3:validator:miner:{miner_hotkey}:{timestamp}"
        
        print(f"   Commitment: {commitment}")
        
        # Sign the commitment
        signature = wallet.hotkey.sign(commitment).hex()
        
        # Prepare request data
        request_data = {
            "hotkey": hotkey,
            "timestamp": timestamp,
            "signature": signature,
            "miner_hotkey": miner_hotkey
        }
        
        print("   Making API request...")
        response = make_request("/get-miner-specific-access", method="POST", data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Miner-specific access granted!")
            print(f"   Target Miner: {data['miner_hotkey']}")
            print(f"   Bucket: {data['bucket']}")
            print(f"   Prefix: {data['prefix']}")
            print(f"   Expiry: {data['expiry']}")
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
    parser = argparse.ArgumentParser(description="Test S3 Auth API locally")
    parser.add_argument("--wallet", required=True, help="Wallet name")
    parser.add_argument("--hotkey", required=True, help="Hotkey name")
    parser.add_argument("--type", choices=["miner", "validator"], required=True, help="Test type")
    parser.add_argument("--miner-hotkey", help="Target miner hotkey for validator miner-specific access")
    
    args = parser.parse_args()
    
    print("🚀 Starting S3 Auth API Local Tests")
    print("=" * 50)
    
    # Test healthcheck first
    if not test_healthcheck():
        print("❌ Healthcheck failed, stopping tests")
        return
    
    print("\n" + "=" * 50)
    
    if args.type == "miner":
        success = test_miner_access(args.wallet, args.hotkey)
    elif args.type == "validator":
        success = test_validator_access(args.wallet, args.hotkey)
        
        # If validator access works and miner hotkey provided, test miner-specific access
        if success and args.miner_hotkey:
            print("\n" + "-" * 30)
            test_miner_specific_access(args.wallet, args.hotkey, args.miner_hotkey)
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Tests completed successfully!")
    else:
        print("❌ Tests failed!")

if __name__ == "__main__":
    main()
