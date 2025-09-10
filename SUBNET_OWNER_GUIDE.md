# Subnet Owner Guide: Activating Subnet 428 and Granting Validator Permissions

**Document ID**: Subnet Owner Guide  
**Title**: How to Activate Testnet Subnet 428 and Grant Validator Permissions  
**Author**: Resi Labs Development Team  
**Date**: December 2024  
**Status**: Active  
**Target Audience**: Subnet 428 Owners and Administrators

## 🎯 Purpose

This guide provides step-by-step instructions for subnet owners to:
1. Activate testnet subnet 428
2. Grant validator permissions to users
3. Manage the testnet environment effectively

## ⚠️ Important Prerequisites

- **Subnet Owner Wallet**: You must have the subnet owner wallet (`resi_subnet`)
- **Sufficient Testnet TAO**: Ensure you have testnet TAO for transactions
- **Network Access**: Stable connection to Bittensor testnet
- **Patience**: Subnet activation has timing restrictions

## 📋 Step-by-Step Process

### **Step 1: Check Subnet Status**

First, verify the current subnet status:

```bash
# Check subnet information
btcli subnets show --netuid 428 --subtensor.network test

# Check your wallet status
btcli wallet overview --wallet.name resi_subnet --subtensor.network test
```

**Expected Output:**
- Subnet should show as "Resi Labs" with your coldkey as owner
- Your validator hotkey should be at position 0
- Subnet status will show as inactive initially

### **Step 2: Wait for Activation Window**

The subnet has timing restrictions for activation:

```bash
# Try to start the subnet (this will show timing info)
btcli subnets start --netuid 428 --subtensor.network test --wallet.name resi_subnet --wallet.hotkey validator
```

**If you see this error:**
```
❌ Failed to start subnet: Subtensor returned `NeedWaitingMoreBlocksToStarCall(Module)` error.
This means: `need wait for more blocks to accept the start call extrinsic.`
```

**What this means:**
- **Minimum start block**: 5388898 (example)
- **Current block**: 5388137 (example)
- **Blocks remaining**: 761 (example)
- **Time to wait**: ~2h 32m (example)

**Action Required:** Wait for the specified time before proceeding.

### **Step 3: Activate the Subnet**

Once the waiting period is over:

```bash
# Activate the subnet
btcli subnets start --netuid 428 --subtensor.network test --wallet.name resi_subnet --wallet.hotkey validator

# Confirm when prompted
Are you sure you want to start subnet 428's emission schedule? [y/n]: y
Enter your password: [enter your wallet password]
```

**Expected Success Output:**
```
🌍  📡 Starting subnet 428's emission schedule...
✅ Subnet 428 started successfully!
```

### **Step 4: Verify Subnet Activation**

Check that the subnet is now active:

```bash
# Check subnet status
btcli subnets show --netuid 428 --subtensor.network test

# Check hyperparameters
btcli sudo get --netuid 428 --subtensor.network test
```

**Look for:**
- `subnet_is_active: True` in hyperparameters
- Active emissions and validator permits

### **Step 5: Grant Validator Permissions**

Now you can grant validator permissions using the weights system:

#### **Method 1: Grant Permission to Your Own Hotkey**

```bash
# Commit weights (this grants validator permission)
btcli weights commit --subtensor.network test --netuid 428 --wallet.name resi_subnet --wallet.hotkey validator

# When prompted:
# UIDs of interest: 0
# Corresponding weights: 1.0
# Salt: 1234
# Confirm: y
```

#### **Method 2: Grant Permission to Another User's Hotkey**

First, find their UID:
```bash
# Check metagraph to find their UID
btcli subnets show --netuid 428 --subtensor.network test
```

Then grant permission:
```bash
# Commit weights for their UID
btcli weights commit --subtensor.network test --netuid 428 --wallet.name resi_subnet --wallet.hotkey validator

# When prompted:
# UIDs of interest: [their_uid]
# Corresponding weights: 1.0
# Salt: 1234
# Confirm: y
```

### **Step 6: Verify Validator Permissions**

Test that validator permissions were granted:

```bash
# Check your validator status
python api-test/test_testnet_s3_auth.py --wallet resi_subnet --hotkey validator --validator-check-only

# Or check another user's status
python api-test/test_testnet_s3_auth.py --wallet [their_wallet] --hotkey [their_hotkey] --validator-check-only
```

**Expected Success Output:**
```
✅ You ARE a validator!
```

## 🔧 Troubleshooting

### **Problem: "SubToken disabled" Error**

**Cause:** Staking is disabled on this testnet  
**Solution:** This is expected - use the weights system instead of staking

### **Problem: "NeedWaitingMoreBlocksToStarCall" Error**

**Cause:** Subnet activation has timing restrictions  
**Solution:** Wait for the specified time period before trying again

### **Problem: "This wallet doesn't own the specified subnet" Error**

**Cause:** Using wrong wallet  
**Solution:** Use the `resi_subnet` wallet (the actual subnet owner)

### **Problem: Weights Commit/Reveal Fails**

**Cause:** Subnet not active or network issues  
**Solution:** 
1. Ensure subnet is active first
2. Check network connectivity
3. Try again after a few minutes

### **Problem: Validator Status Not Updating**

**Cause:** Blockchain state not yet updated  
**Solution:** Wait 1-2 minutes and check again

## 📊 Managing Multiple Validators

### **Adding Multiple Validators**

```bash
# Grant permission to multiple UIDs at once
btcli weights commit --subtensor.network test --netuid 428 --wallet.name resi_subnet --wallet.hotkey validator

# When prompted:
# UIDs of interest: 0,1,2,3
# Corresponding weights: 1.0,1.0,1.0,1.0
# Salt: 1234
# Confirm: y
```

### **Removing Validator Permissions**

```bash
# Set weight to 0 to remove validator permission
btcli weights commit --subtensor.network test --netuid 428 --wallet.name resi_subnet --wallet.hotkey validator

# When prompted:
# UIDs of interest: [uid_to_remove]
# Corresponding weights: 0.0
# Salt: 1234
# Confirm: y
```

## 🎯 Best Practices

### **For Subnet Owners:**

1. **Monitor Subnet Health**: Regularly check subnet status and validator counts
2. **Manage Validator Slots**: Keep track of who has validator permissions
3. **Test Before Production**: Use testnet to validate changes before mainnet
4. **Document Changes**: Keep records of validator permission grants/revocations

### **For Validator Management:**

1. **Verify Before Granting**: Confirm users are registered on the subnet first
2. **Use Consistent Weights**: Grant equal weights to all validators (1.0)
3. **Monitor Performance**: Check that validators are actively participating
4. **Clean Up Inactive**: Remove permissions from inactive validators

## 📞 Support and Maintenance

### **Regular Maintenance Tasks:**

```bash
# Weekly: Check subnet status
btcli subnets show --netuid 428 --subtensor.network test

# Weekly: Check validator count
python api-test/test_testnet_s3_auth.py --wallet resi_subnet --hotkey validator --validator-check-only

# As needed: Grant/revoke validator permissions
btcli weights commit --subtensor.network test --netuid 428 --wallet.name resi_subnet --wallet.hotkey validator
```

### **Emergency Procedures:**

If the subnet becomes unstable:
1. Check network connectivity
2. Verify wallet access
3. Contact Bittensor support if needed
4. Consider restarting the subnet if necessary

## 🚀 Next Steps

Once the subnet is active and validator permissions are granted:

1. **Test Validator Access**: Use the API test scripts to verify functionality
2. **Monitor Performance**: Watch for any issues with validator operations
3. **Scale Gradually**: Add more validators as needed
4. **Prepare for Mainnet**: Use testnet experience to improve mainnet operations

---

**Ready to activate your subnet?** Follow the steps above and you'll have a fully functional testnet with validator permissions! 🎉
