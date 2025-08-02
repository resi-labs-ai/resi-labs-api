"""
Optimized Bittensor utility functions using cached metagraph
Solves timeout issues by avoiding repeated blockchain calls
"""
import time
import bittensor as bt
from typing import Optional
from bittensor import Keypair


def is_hotkey_registered_cached(hotkey: str, metagraph: bt.metagraph) -> bool:
    """
    Check if a hotkey is registered using cached metagraph.
    
    Args:
        hotkey: The hotkey to check
        metagraph: Cached metagraph from MetagraphSyncer
        
    Returns:
        bool: True if hotkey is registered in the metagraph
    """
    try:
        return hotkey in metagraph.hotkeys
    except Exception as e:
        print(f"Error checking hotkey registration: {str(e)}")
        return False


def verify_signature_cached(message: str, signature_hex: str, hotkey_ss58: str, metagraph: bt.metagraph) -> bool:
    """
    Verify that the message was signed by the hotkey using cached metagraph.
    Also ensures the hotkey is registered in the cached metagraph.
    
    Args:
        message: The message that was signed
        signature_hex: The signature in hex format
        hotkey_ss58: The hotkey address in SS58 format
        metagraph: Cached metagraph from MetagraphSyncer
        
    Returns:
        bool: True if signature is valid and hotkey is registered
    """
    try:
        # First check if hotkey is registered using cached metagraph
        if not is_hotkey_registered_cached(hotkey_ss58, metagraph):
            print(f"Hotkey {hotkey_ss58} is not registered in cached metagraph")
            return False
        
        # Verify cryptographic signature (this is fast - ~1ms)
        kp = Keypair(ss58_address=hotkey_ss58)
        signature = bytes.fromhex(signature_hex)
        return kp.verify(message.encode(), signature)
    except Exception as e:
        print(f"Signature verification error: {e}")
        return False


def verify_validator_status_cached(hotkey: str, metagraph: bt.metagraph) -> bool:
    """
    Check if a hotkey belongs to a validator with a permit using cached metagraph.
    
    Args:
        hotkey: The hotkey to check
        metagraph: Cached metagraph from MetagraphSyncer
        
    Returns:
        bool: True if hotkey is a validator with permit and sufficient stake
    """
    try:
        # Check if hotkey is in the metagraph
        if hotkey not in metagraph.hotkeys:
            return False
        
        # Get the UID for this hotkey
        uid = metagraph.hotkeys.index(hotkey)
        
        # Check validator permit and stake requirements
        validator_permit = bool(metagraph.validator_permit[uid])
        stake = int(metagraph.alpha_stake[uid]) > 40_000
        
        if validator_permit and stake:
            return True
        
        return False
    except Exception as e:
        print(f"Error verifying validator status: {str(e)}")
        return False


def get_commitment_cached(hotkey: str, metagraph: bt.metagraph, subtensor: bt.subtensor, netuid: int) -> Optional[str]:
    """
    Get the latest commitment from the blockchain using cached metagraph for UID lookup.
    
    Args:
        hotkey: The hotkey to get commitment for
        metagraph: Cached metagraph from MetagraphSyncer
        subtensor: Subtensor connection (reused, not created per call)
        netuid: Network UID
        
    Returns:
        Optional[str]: The commitment string or None if not found
    """
    try:
        # Use cached metagraph to get UID quickly
        if hotkey not in metagraph.hotkeys:
            print(f"Hotkey {hotkey} not registered in cached metagraph")
            return None
        
        uid = metagraph.hotkeys.index(hotkey)
        
        # Get commitment from blockchain (this is the only blockchain call)
        commitment = subtensor.get_commitment(netuid=netuid, uid=uid)
        return commitment
    except Exception as e:
        print(f"Error getting commitment: {str(e)}")
        return None


def verify_commitment_cached(
        hotkey: str,
        expected_prefix: str,
        metagraph: bt.metagraph,
        subtensor: bt.subtensor,
        netuid: int,
        max_age_seconds: int = 60
) -> bool:
    """
    Verify that a commitment exists and matches the expected format, within the time window.
    Uses cached metagraph for faster UID resolution.
    
    Args:
        hotkey: The hotkey to check
        expected_prefix: The expected prefix of the commitment
        metagraph: Cached metagraph from MetagraphSyncer
        subtensor: Subtensor connection (reused, not created per call)
        netuid: Network UID
        max_age_seconds: Maximum age of commitment in seconds
        
    Returns:
        bool: True if commitment is valid and recent
    """
    # Get commitment using cached metagraph
    commitment = get_commitment_cached(hotkey, metagraph, subtensor, netuid)
    if not commitment:
        return False

    try:
        # Check if it starts with expected prefix
        if not commitment.startswith(expected_prefix):
            return False

        # For validator, additionally verify validator status using cached metagraph
        if "validator" in expected_prefix and not verify_validator_status_cached(hotkey, metagraph):
            return False

        # Check if commitment timestamp is within allowed window
        parts = commitment.split(":")
        if len(parts) < 2:
            return False

        # Get timestamp from last part
        try:
            timestamp = int(parts[-1])
            current_time = int(time.time())

            # Check if commitment is not too old
            if (current_time - timestamp) > max_age_seconds:
                print(f"Commitment too old: {current_time - timestamp} seconds")
                return False

            return True
        except ValueError:
            print(f"Invalid timestamp in commitment: {parts[-1]}")
            return False

    except Exception as e:
        print(f"Error validating commitment: {str(e)}")
        return False