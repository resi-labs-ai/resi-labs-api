#!/usr/bin/env python3
"""
Test signature verification manually
"""

import time
import bittensor as bt
from s3_storage_api.utils.bt_utils import verify_signature

# Load your wallet
wallet_name = "428_testnet_validator"
hotkey_name = "428_testnet_validator_hotkey"

print(f"Loading wallet: {wallet_name}, hotkey: {hotkey_name}")
wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)

coldkey = wallet.coldkey.ss58_address
hotkey = wallet.hotkey.ss58_address

print(f"Coldkey: {coldkey}")
print(f"Hotkey: {hotkey}")

# Create commitment and sign it
timestamp = int(time.time())
commitment = f"s3:data:access:{coldkey}:{hotkey}:{timestamp}"
print(f"Commitment: {commitment}")

# Sign the commitment
signature = wallet.hotkey.sign(commitment).hex()
print(f"Signature: {signature}")

# Test verification
print("\nTesting signature verification...")
try:
    is_valid = verify_signature(commitment, signature, hotkey, 428, "test")
    print(f"Signature valid: {is_valid}")
except Exception as e:
    print(f"Error verifying signature: {e}")

# Test with metagraph directly
print("\nTesting with metagraph directly...")
try:
    subtensor = bt.subtensor(network="test")
    metagraph = subtensor.metagraph(netuid=428)
    
    # Find the hotkey in metagraph
    if hotkey in metagraph.hotkeys:
        hotkey_idx = metagraph.hotkeys.index(hotkey)
        print(f"Hotkey found at index: {hotkey_idx}")
        
        # Get the actual hotkey object from metagraph
        metagraph_hotkey = metagraph.hotkeys[hotkey_idx]
        print(f"Metagraph hotkey: {metagraph_hotkey}")
        
        # Try to verify signature with keypair
        try:
            # Create a keypair from the hotkey address
            keypair = bt.Keypair(ss58_address=hotkey)
            signature_bytes = bytes.fromhex(signature)
            is_valid_direct = keypair.verify(commitment, signature_bytes)
            print(f"Direct keypair verification: {is_valid_direct}")
        except Exception as e:
            print(f"Direct verification error: {e}")
            
    else:
        print(f"Hotkey {hotkey} not found in metagraph")
        
except Exception as e:
    print(f"Error with metagraph: {e}")
