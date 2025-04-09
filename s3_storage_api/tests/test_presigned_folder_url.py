import boto3
import json
from datetime import datetime, timedelta
import base64
import hmac
import hashlib
import requests
import os
import pandas as pd
import numpy as np

# 1. Set your AWS credentials and bucket info
ACCESS_KEY = ''
SECRET_KEY = ''
BUCKET = ''
COLDKEY = 'test_coldkey_1234'
SOURCE = 'x'

# 2. Create S3 client
s3 = boto3.client(
  's3',
  aws_access_key_id=ACCESS_KEY,
  aws_secret_access_key=SECRET_KEY,
  region_name='us-east-1'
)

# 3. Generate folder upload policy with SIMPLER security
def get_folder_policy():
  folder_prefix = f"data/{SOURCE}/{COLDKEY}/"
  expiration = datetime.utcnow() + timedelta(hours=24)

  # SIMPLIFIED policy - removed Content-Type restrictions
  policy = {
      "expiration": expiration.strftime("%Y-%m-%dT%H:%M:%SZ"),
      "conditions": [
          # Exact bucket match
          {"bucket": BUCKET},

          # Folder prefix match
          ["starts-with", "$key", folder_prefix],

          # File access control
          {"acl": "private"},

          # File size limits (1KB to 1GB) - lowered minimum size
          ["content-length-range", 1024, 1073741824]
      ]
  }

  policy_json = json.dumps(policy).encode('utf-8')
  policy_base64 = base64.b64encode(policy_json).decode('utf-8')

  signature = base64.b64encode(
      hmac.new(
          SECRET_KEY.encode('utf-8'),
          policy_base64.encode('utf-8'),
          hashlib.sha1
      ).digest()
  ).decode('utf-8')

  return {
      "url": f"https://{BUCKET}.s3.amazonaws.com/",
      "folder": folder_prefix,
      "expiry": expiration.isoformat(),
      "fields": {
          "acl": "private",
          "policy": policy_base64,
          "AWSAccessKeyId": ACCESS_KEY,
          "signature": signature
      }
  }

# 4. Verify policy security
def analyze_policy_security(policy):
  """Analyze the security of a policy and report constraints"""
  print("\n=== Policy Security Analysis ===")

  # Decode the policy to check its constraints
  policy_base64 = policy['fields']['policy']
  policy_json = base64.b64decode(policy_base64).decode('utf-8')
  policy_data = json.loads(policy_json)

  print(f"Policy Expiration: {policy_data['expiration']}")
  print("\nSecurity Constraints:")

  # Analyze each condition
  for condition in policy_data['conditions']:
      if isinstance(condition, dict):
          for key, value in condition.items():
              print(f"• {key}: {value}")
      elif isinstance(condition, list):
          print(f"• {condition[0]} {condition[1]}: {condition[2] if len(condition) > 2 else ''}")

  # Security recommendations
  print("\nSecurity Assessment:")

  # Check bucket restriction
  bucket_restricted = False
  for condition in policy_data['conditions']:
      if isinstance(condition, dict) and 'bucket' in condition:
          bucket_restricted = True
          break
  print(f"• Bucket restriction: {'✅ Enforced' if bucket_restricted else '❌ Missing'}")

  # Check folder restriction
  folder_restricted = False
  for condition in policy_data['conditions']:
      if isinstance(condition, list) and condition[0] == 'starts-with' and condition[1] == '$key':
          folder_restricted = True
          break
  print(f"• Folder restriction: {'✅ Enforced' if folder_restricted else '❌ Missing'}")

  # Check size restriction
  size_restricted = False
  for condition in policy_data['conditions']:
      if isinstance(condition, list) and condition[0] == 'content-length-range':
          size_restricted = True
          max_size_mb = condition[2] / (1024 * 1024)
          print(f"• Size restriction: ✅ Enforced (Max: {max_size_mb:.2f} MB)")
          break
  if not size_restricted:
      print("• Size restriction: ❌ Missing")

  # Check expiration
  expiry = datetime.strptime(policy_data['expiration'], "%Y-%m-%dT%H:%M:%SZ")
  now = datetime.utcnow()
  hours_valid = (expiry - now).total_seconds() / 3600
  if hours_valid <= 24:
      print(f"• Time restriction: ✅ Good (Valid for {hours_valid:.1f} hours)")
  else:
      print(f"• Time restriction: ⚠️ Long validity ({hours_valid:.1f} hours)")

  return bucket_restricted and folder_restricted

# 5. Create test parquet file
def create_test_file(filename, rows=1000):
  # Create random data
  data = {
      'datetime': [datetime.now() for _ in range(rows)],
      'content': [f'Test content {i}' for i in range(rows)],
      'value': np.random.rand(rows)
  }

  # Create DataFrame
  df = pd.DataFrame(data)

  # Save as parquet
  os.makedirs('temp', exist_ok=True)
  filepath = f"temp/{filename}"
  df.to_parquet(filepath)

  return filepath

# 6. Upload using the policy - FIXED VERSION
def upload_with_policy(policy, local_file, s3_key):
  """
  Uploads a local file to an S3 bucket using a pre-signed POST policy.
  """
  # Create POST data with all required fields
  post_data = {
      'key': s3_key,
      'acl': 'private',
      'AWSAccessKeyId': policy['fields']['AWSAccessKeyId'],
      'policy': policy['fields']['policy'],
      'signature': policy['fields']['signature'],
  }

  # If x-amz-storage-class is in policy fields, include it
  if 'x-amz-storage-class' in policy['fields']:
      post_data['x-amz-storage-class'] = policy['fields']['x-amz-storage-class']

  # Open the file in binary mode
  with open(local_file, 'rb') as f:
      # Simplified - no Content-Type settings
      files = {'file': f}

      # Perform the POST request
      response = requests.post(
          policy['url'],
          data=post_data,
          files=files
      )

  # Check response
  if response.status_code == 204:
      print(f"✅ Uploaded {local_file} to {s3_key}")
      return True
  else:
      print(f"❌ Failed to upload {local_file}: {response.status_code}")
      print(response.text)
      return False

# 7. Test uploading to wrong folder
def test_policy_restrictions(policy):
  """Test if the policy restrictions are working correctly"""
  print("\n=== Testing Policy Restrictions ===")

  # Create a test file
  test_file = create_test_file("policy_test.parquet")

  # Try to upload to wrong folder (should fail)
  wrong_folder = f"wrong_folder/{COLDKEY}/policy_test.parquet"
  print("\nTesting wrong folder upload (should fail):")
  wrong_folder_result = upload_with_policy(policy, test_file, wrong_folder)

  # Cleanup
  os.remove(test_file)

  return not wrong_folder_result  # Should return True if restrictions worked

# 8. Test everything
def run_test():
  print("\n=== Testing S3 Folder Upload Policy ===")

  # Get upload policy for folder
  policy = get_folder_policy()
  print(f"Got upload policy for folder: {policy['folder']}")
  print(f"Policy expires: {policy['expiry']}")

  # Analyze policy security
  analyze_policy_security(policy)

  # Test policy restrictions
  restrictions_working = test_policy_restrictions(policy)
  print(f"\nPolicy restrictions working: {'✅ Yes' if restrictions_working else '❌ No'}")

  # Create and upload multiple files
  print("\n=== Testing Normal Uploads ===")
  for i in range(3):
      # Create file
      filename = f"test_data_{i}_{int(datetime.now().timestamp())}.parquet"
      filepath = create_test_file(filename)

      # Upload using policy
      s3_key = f"{policy['folder']}{filename}"
      upload_with_policy(policy, filepath, s3_key)

      # Clean up
      os.remove(filepath)

  # Verify uploads by listing the folder
  print("\nVerifying uploads...")
  response = s3.list_objects_v2(
      Bucket=BUCKET,
      Prefix=policy['folder']
  )

  if 'Contents' in response:
      print(f"\nFiles in {policy['folder']}:")
      for obj in response['Contents']:
          print(f"  • {obj['Key']} ({obj['Size'] / 1024 / 1024:.2f} MB)")
  else:
      print(f"No files found in {policy['folder']}")

  print("\n=== Test Complete ===")

# Run the test
if __name__ == "__main__":
  run_test()