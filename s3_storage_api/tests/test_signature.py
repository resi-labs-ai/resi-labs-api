"""
Test script to validate that Bittensor signature verification works as expected
"""
import time
import argparse
import bittensor as bt
from substrateinterface import Keypair

def test_signature_verification():
    """Test Bittensor signature verification with a real wallet"""
    print("Starting signature verification test...")

    # Step 1: Load a wallet (will use test one if specified or create a temporary one)
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--wallet", type=str, help="Wallet name to use for testing")
        parser.add_argument("--hotkey", type=str, help="Hotkey name to use for testing")
        args = parser.parse_args()

        if args.wallet and args.hotkey:
            print(f"Using provided wallet: {args.wallet} and hotkey: {args.hotkey}")
            wallet = bt.wallet(name=args.wallet, hotkey=args.hotkey)
        else:
            print("Creating temporary wallet for testing...")
            wallet = bt.wallet(name="temp_test_wallet", hotkey="test_hotkey")
            wallet.create()
            print("Created temporary wallet")

        print(f"Wallet hotkey: {wallet.hotkey.ss58_address}")

        # Step 2: Create a test message
        timestamp = int(time.time())
        expiry = timestamp + 3600
        coldkey = wallet.coldkey.ss58_address
        hotkey = wallet.hotkey.ss58_address
        source = "x"

        test_message = f"folder:{coldkey}:{hotkey}:{source}:{timestamp}:{expiry}"
        print(f"Test message: {test_message}")

        # Step 3: Sign the message
        message_bytes = test_message.encode('utf-8')
        signature = wallet.hotkey.sign(message_bytes)
        signature_hex = "0x" + signature.hex()
        print(f"Signature: {signature_hex}")

        # Step 4: Verify with our implementation
        print("\nTesting verification...")

        # Convert signature from hex if needed
        if signature_hex.startswith('0x'):
            verification_signature = bytes.fromhex(signature_hex[2:])
        else:
            verification_signature = bytes.fromhex(signature_hex)

        keypair = Keypair(ss58_address=hotkey)
        is_valid = keypair.verify(message_bytes, verification_signature)

        print(f"Verification result: {'SUCCESS' if is_valid else 'FAILURE'}")

        # Step 5: Test incorrect signature to ensure verification fails when it should
        print("\nTesting with incorrect signature...")
        incorrect_signature = bytes([b ^ 0x01 for b in verification_signature])  # Flip some bits
        is_valid_bad = keypair.verify(message_bytes, incorrect_signature)

        print(f"Incorrect signature rejection: {'SUCCESS' if not is_valid_bad else 'FAILURE - should have rejected'}")

        # Step 6: Test incorrect message to ensure verification fails
        print("\nTesting with incorrect message...")
        bad_message = f"folder:{coldkey}:{hotkey}:{source}:{timestamp + 1}:{expiry}"
        bad_message_bytes = bad_message.encode('utf-8')
        is_valid_bad_msg = keypair.verify(bad_message_bytes, verification_signature)

        print(f"Incorrect message rejection: {'SUCCESS' if not is_valid_bad_msg else 'FAILURE - should have rejected'}")

        # Final verdict
        if is_valid and not is_valid_bad and not is_valid_bad_msg:
            print("\n✅ VERIFICATION SYSTEM WORKING CORRECTLY")
            return True
        else:
            print("\n❌ VERIFICATION SYSTEM NOT WORKING AS EXPECTED")
            return False

    except Exception as e:
        print(f"Error during testing: {str(e)}")
        return False


if __name__ == "__main__":
    test_signature_verification()