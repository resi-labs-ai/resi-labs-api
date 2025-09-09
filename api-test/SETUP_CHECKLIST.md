# Setup Verification Checklist for Subnet 46

## 📋 Pre-Test Checklist

Before running the S3 API test, verify you have completed all these requirements:

### ✅ System Requirements

- [ ] **Python 3.8+** installed
  ```bash
  python --version  # Should show 3.8 or higher
  ```

- [ ] **Required packages** installed
  ```bash
  pip install bittensor requests
  ```

- [ ] **Internet connection** working
  ```bash
  ping google.com
  ```

### ✅ Wallet Requirements

- [ ] **Wallet exists** in `~/.bittensor/wallets/`
  ```bash
  ls ~/.bittensor/wallets/
  ```

- [ ] **Wallet name and hotkey name** are known
  ```bash
  btcli wallets list
  ```

- [ ] **Wallet password** is available (if encrypted)

### ✅ Network Registration

- [ ] **Subnet 46 exists** on mainnet
  ```bash
  btcli subnet list --subtensor.network finney | grep -A3 -B3 "46\|Resi"
  ```

- [ ] **Hotkey is registered** on subnet 46
  ```bash
  btcli subnet metagraph --subtensor.network finney --netuid 46 | grep YOUR_HOTKEY_ADDRESS
  ```

- [ ] **Registration is confirmed** (not pending)

### ✅ Validator-Specific Requirements (if applicable)

- [ ] **Sufficient stake** for validator permissions (typically 1000+ TAO)
- [ ] **Validator permit** is active
- [ ] **Validator infrastructure** is ready

### ✅ API Accessibility

- [ ] **API endpoint** is accessible
  ```bash
  curl -s https://s3-auth-api.resilabs.ai/healthcheck
  ```

- [ ] **Firewall/VPN** allows HTTPS traffic to resilabs.ai

## 🚀 Running the Test

Once all checklist items are complete:

1. **Download the test script**:
   ```bash
   wget https://raw.githubusercontent.com/your-repo/api-test/test_mainnet_s3_auth.py
   # OR copy from the documentation
   ```

2. **Run the test**:
   ```bash
   python test_mainnet_s3_auth.py --wallet YOUR_WALLET_NAME --hotkey YOUR_HOTKEY_NAME
   ```

3. **Expected success indicators**:
   - ✅ API health check passes
   - ✅ Wallet loads successfully
   - ✅ Hotkey registration confirmed
   - ✅ Authentication succeeds
   - ✅ S3 credentials received

## 🔧 Troubleshooting Quick Fixes

### "Cannot connect to API"
```bash
# Test API connectivity
curl -v https://s3-auth-api.resilabs.ai/healthcheck

# Check DNS resolution
nslookup s3-auth-api.resilabs.ai
```

### "Wallet loading failed"
```bash
# Verify wallet files exist
ls -la ~/.bittensor/wallets/YOUR_WALLET_NAME/

# Check permissions
chmod 600 ~/.bittensor/wallets/YOUR_WALLET_NAME/coldkey
chmod 600 ~/.bittensor/wallets/YOUR_WALLET_NAME/hotkeys/YOUR_HOTKEY_NAME
```

### "Hotkey not registered"
```bash
# Register on subnet 46
btcli subnet register --subtensor.network finney --netuid 46 --wallet.name YOUR_WALLET --wallet.hotkey YOUR_HOTKEY

# Verify registration
btcli subnet metagraph --subtensor.network finney --netuid 46
```

### "Not a validator"
```bash
# Check validator status
btcli subnet metagraph --subtensor.network finney --netuid 46 | grep -A5 -B5 YOUR_HOTKEY

# Verify stake amount
btcli wallet overview --wallet.name YOUR_WALLET
```

## ✅ Success Criteria

Your setup is ready when the test script shows:

```
============================================================
                         Test Results                     
============================================================

✅ 🎉 SUCCESS! Your wallet can authenticate with the S3 API
✅ You're ready to participate in subnet 46!
```

## 📞 Support

If you encounter issues after completing this checklist:

1. **Re-run the test** with `--skip-health` if API is temporarily down
2. **Check the documentation** for detailed troubleshooting
3. **Contact support** with your test output
4. **Join the community** for peer assistance

---

**Complete this checklist before testing to ensure a smooth experience!** ✨
