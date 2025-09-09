# Expected API Responses - Valid Success Cases

This document shows exactly what successful API responses look like, so you can see what valid authentication and S3 credential responses should contain.

## 🏥 Health Check Response

**Endpoint**: `GET /healthcheck`

**Successful Response** (HTTP 200):
```json
{
  "status": "ok",
  "timestamp": 1757443855.4194062,
  "bucket": "1000-resilabs-caleb-dev-bittensor-sn46-datacollection",
  "region": "us-east-2",
  "folder_structure": "data/hotkey={hotkey_id}/job_id={job_id}/",
  "s3_ok": true,
  "s3_latency_ms": 30.23,
  "redis_ok": true,
  "metagraph_syncer": {
    "enabled": true,
    "netuid": 46,
    "sync_interval": 300,
    "hotkeys_count": 88,
    "last_sync": "recent"
  },
  "stats": {
    "uptime_hours": 0.06,
    "total_requests": 7,
    "total_errors": 2,
    "total_timeouts": 0,
    "error_rate": 0.2857142857142857,
    "timeout_rate": 0.0,
    "requests_per_hour": 118.76883665750722
  },
  "timeouts": {
    "validator_verification": "120s",
    "signature_verification": "60s",
    "s3_operations": "60s"
  }
}
```

**Key Success Indicators**:
- ✅ `status: "ok"`
- ✅ `s3_ok: true`
- ✅ `redis_ok: true`
- ✅ `bucket` name is present
- ✅ `metagraph_syncer.enabled: true` (preferred, but fallback methods work too)

## ⛏️ Miner Access Response

**Endpoint**: `POST /get-folder-access`

**Request Payload**:
```json
{
  "coldkey": "5HTdjNKg4pbKLgzRSHLLvWmHTM3893BqjNfe3L7yaXfi789Y",
  "hotkey": "5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni",
  "timestamp": 1703123456,
  "signature": "fc27f1a06424f777ef2bc9d0adc113dfca03571ae516c8f3aa6168406064d04d3473f124d0b170767cf1a30e5041641b8a824e511272510df5a053ad3bf56c8f"
}
```

**Successful Response** (HTTP 200):
```json
{
  "folder": "data/hotkey=5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni/",
  "url": "https://1000-resilabs-caleb-dev-bittensor-sn46-datacollection.s3.us-east-2.amazonaws.com",
  "fields": {
    "acl": "private",
    "key": "data/hotkey=5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni/${filename}",
    "AWSAccessKeyId": "AKIAXX7LRNI5KWU23AWX",
    "policy": "eyJ2ZXJzaW9uIjoiMjAxMi0xMC0xNyIsImNvbmRpdGlvbnMiOlt7ImFjbCI6InByaXZhdGUifSx7ImJ1Y2tldCI6IjEwMDAtcmVzaWxhYnMtY2FsZWItZGV2LWJpdHRlbnNvci1zbjQ2LWRhdGFjb2xsZWN0aW9uIn0seyJrZXkiOiJkYXRhL2hvdGtleT01RktpNFRpQkNmNzZ2ek5xaUJXWlJVMmtLZmJXZTd2ZkRmSFQ4cGNZVTdmckRvbmkvJHtmaWxlbmFtZX0ifSxbImNvbnRlbnQtbGVuZ3RoLXJhbmdlIiwxMDI0LDUzNjg3MDkxMjBdLHsieC1hbXotc3RvcmFnZS1jbGFzcyI6IlNUQU5EQVJEIn1dLCJleHBpcmF0aW9uIjoiMjAyNC0xMi0yNlQxNTozMDowMFoifQ==",
    "signature": "abc123def456...",
    "x-amz-storage-class": "STANDARD"
  },
  "expiry": "2024-12-26T15:30:00",
  "list_url": "https://1000-resilabs-caleb-dev-bittensor-sn46-datacollection.s3.us-east-2.amazonaws.com?list-type=2&prefix=data%2Fhotkey%3D5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni%2F&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXX7LRNI5KWU23AWX%2F20241225%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20241225T123000Z&X-Amz-Expires=10800&X-Amz-SignedHeaders=host&X-Amz-Signature=...",
  "structure_info": {
    "folder_structure": "data/hotkey={hotkey_id}/job_id={job_id}/",
    "description": "Upload files to job_id folders within your hotkey directory under data/ prefix"
  }
}
```

**Key Success Indicators**:
- ✅ HTTP 200 status code
- ✅ `folder` contains your hotkey address
- ✅ `url` points to the S3 bucket
- ✅ `fields` contains all required upload parameters:
  - `key` with your hotkey path
  - `AWSAccessKeyId`
  - `policy` (base64 encoded)
  - `signature`
  - `acl: "private"`
- ✅ `expiry` shows future timestamp
- ✅ `list_url` for viewing your uploaded files
- ✅ `structure_info` explains folder organization

## 👑 Validator Access Response

**Endpoint**: `POST /get-validator-access`

**Request Payload**:
```json
{
  "hotkey": "5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni",
  "timestamp": 1703123456,
  "signature": "0c6e50361d5c65adbae0ad3f2879c146e246663269113aa171b4e5021fc8066b822b6e216fa89db6c5a5f80c7f7c387d22a13513773b86a7fe6186581075208a"
}
```

**Successful Response** (HTTP 200):
```json
{
  "bucket": "1000-resilabs-caleb-dev-bittensor-sn46-datacollection",
  "region": "us-east-2",
  "validator_hotkey": "5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni",
  "expiry": "2024-12-26T15:30:00",
  "expiry_seconds": 86400,
  "urls": {
    "global": {
      "list_all_data": "https://1000-resilabs-caleb-dev-bittensor-sn46-datacollection.s3.us-east-2.amazonaws.com?list-type=2&prefix=data%2Fhotkey%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXX7LRNI5KWU23AWX%2F20241225%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20241225T123000Z&X-Amz-Expires=86400&X-Amz-SignedHeaders=host&X-Amz-Signature=..."
    },
    "miners": {
      "list_all_miners": "https://1000-resilabs-caleb-dev-bittensor-sn46-datacollection.s3.us-east-2.amazonaws.com?list-type=2&prefix=data%2Fhotkey%3D&delimiter=%2F&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXX7LRNI5KWU23AWX%2F20241225%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20241225T123000Z&X-Amz-Expires=86400&X-Amz-SignedHeaders=host&X-Amz-Signature=..."
    }
  },
  "structure_info": {
    "folder_structure": "data/hotkey={hotkey_id}/job_id={job_id}/",
    "description": "Job-based folder structure with explicit hotkey and job_id labels under data/ prefix"
  }
}
```

**Key Success Indicators**:
- ✅ HTTP 200 status code
- ✅ `bucket` and `region` specified
- ✅ `validator_hotkey` matches your hotkey
- ✅ `expiry` shows future timestamp
- ✅ `urls.global.list_all_data` for accessing all data
- ✅ `urls.miners.list_all_miners` for listing all miners
- ✅ `structure_info` explains data organization

## 🔍 Validator Miner-Specific Access Response

**Endpoint**: `POST /get-miner-specific-access`

**Request Payload**:
```json
{
  "hotkey": "5FKi4TiBCf76vzNqiBWZRU2kKfbWe7vfDfHT8pcYU7frDoni",
  "timestamp": 1703123456,
  "signature": "1a2b3c4d5e6f...",
  "miner_hotkey": "5DvggEsdjznNNvnQ4q6B52JTsSfYCWbCcJRFyMSrYvoZzutr"
}
```

**Successful Response** (HTTP 200):
```json
{
  "bucket": "1000-resilabs-caleb-dev-bittensor-sn46-datacollection",
  "region": "us-east-2",
  "miner_hotkey": "5DvggEsdjznNNvnQ4q6B52JTsSfYCWbCcJRFyMSrYvoZzutr",
  "miner_url": "https://1000-resilabs-caleb-dev-bittensor-sn46-datacollection.s3.us-east-2.amazonaws.com?list-type=2&prefix=data%2Fhotkey%3D5DvggEsdjznNNvnQ4q6B52JTsSfYCWbCcJRFyMSrYvoZzutr%2F&max-keys=10000&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAXX7LRNI5KWU23AWX%2F20241225%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20241225T123000Z&X-Amz-Expires=10800&X-Amz-SignedHeaders=host&X-Amz-Signature=...",
  "prefix": "data/hotkey=5DvggEsdjznNNvnQ4q6B52JTsSfYCWbCcJRFyMSrYvoZzutr/",
  "expiry": "2024-12-26T15:30:00"
}
```

**Key Success Indicators**:
- ✅ HTTP 200 status code
- ✅ `miner_hotkey` matches requested miner
- ✅ `miner_url` provides access to specific miner's data
- ✅ `prefix` shows the miner's folder path
- ✅ `expiry` shows future timestamp

## ❌ Common Error Responses

### Invalid Signature (HTTP 401)
```json
{
  "detail": "Invalid signature"
}
```

### Not a Validator (HTTP 401)
```json
{
  "detail": "You are not validator"
}
```

### Rate Limited (HTTP 429)
```json
{
  "detail": "Daily limit of 20 exceeded."
}
```

### Invalid Timestamp (HTTP 400)
```json
{
  "detail": "Invalid timestamp"
}
```

### Hotkey Not Registered (HTTP 401)
```json
{
  "detail": "Invalid signature"
}
```
*Note: This often appears as "Invalid signature" when the hotkey isn't registered*

## 🧪 How to Use These Examples

### For Testing Your Implementation:
1. **Compare response structure** - Your successful responses should match these formats
2. **Verify all required fields** - Make sure you receive all the fields shown
3. **Check data types** - Ensure strings, numbers, and booleans match expected types
4. **Validate URLs** - The presigned URLs should be properly formatted and accessible

### For Debugging Issues:
1. **Compare your request format** - Ensure your requests match the example payloads
2. **Check response codes** - HTTP 200 indicates success, anything else needs investigation
3. **Examine error messages** - Match error responses to identify specific issues
4. **Verify timestamps** - Ensure your timestamps are current and within acceptable range

### For Integration:
1. **Parse response fields** - Extract the specific fields your application needs
2. **Handle expiry times** - Use the `expiry` field to refresh credentials before they expire
3. **Use presigned URLs** - The URLs in responses are ready to use for S3 operations
4. **Follow folder structure** - Upload files according to the `structure_info` guidance

---

**These examples represent real, working API responses from a properly configured system.** Use them as a reference for what successful authentication and S3 credential generation should look like! 🎯
