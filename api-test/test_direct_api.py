#!/usr/bin/env python3
"""
Direct API test with manual signature verification
"""

import time
import requests
import bittensor as bt

# API Configuration
API_BASE_URL = "http://localhost:8000"

def test_miner_access():
    # Load wallet
    wallet = bt.wallet(name="428_testnet_validator", hotkey="428_testnet_validator_hotkey")
    
    coldkey = wallet.coldkey.ss58_address
    hotkey = wallet.hotkey.ss58_address
    
    print(f"Coldkey: {coldkey}")
    print(f"Hotkey: {hotkey}")
    
    # Create commitment and signature
    timestamp = int(time.time())
    commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
    signature = wallet.hotkey.sign(commitment).hex()
    
    print(f"Commitment: {commitment}")
    print(f"Signature: {signature}")
    
    # Test signature locally first
    from s3_storage_api.utils.bt_utils import verify_signature
    try:
        is_valid_local = verify_signature(commitment, signature, hotkey, 428, "test")
        print(f"Local signature verification: {is_valid_local}")
    except Exception as e:
        print(f"Local verification error: {e}")
    
    # Prepare request data
    request_data = {
        "coldkey": coldkey,
        "hotkey": hotkey,
        "timestamp": timestamp,
        "signature": signature
    }
    
    print("\nMaking API request...")
    try:
        response = requests.post(f"{API_BASE_URL}/get-folder-access", json=request_data)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Folder: {data.get('folder')}")
        else:
            print("❌ FAILED")
            
    except Exception as e:
        print(f"Request error: {e}")

if __name__ == "__main__":
    test_miner_access()
