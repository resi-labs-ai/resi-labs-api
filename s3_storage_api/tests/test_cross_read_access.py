import boto3
import json
from datetime import datetime, timedelta
import base64
import hmac
import hashlib
import requests
import os

# AWS credentials
ACCESS_KEY = ''
SECRET_KEY = '//z'
BUCKET = 'data-universe-storage'

# The two folders we want to test
FOLDER_WITH_POLICY = 'data/x/test_coldkey_1234/'
FOLDER_TO_ACCESS = 'data/x/test_coldkey_123/'

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name='us-east-1'
)


def get_folder_policy(folder_prefix):
    """Generate a policy for a specific folder"""
    expiration = datetime.utcnow() + timedelta(hours=24)

    policy = {
        "expiration": expiration.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "conditions": [
            {"bucket": BUCKET},
            ["starts-with", "$key", folder_prefix],
            {"acl": "private"},
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


def list_files_in_folder(folder):
    """List files in a folder using direct S3 client"""
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET,
            Prefix=folder
        )

        if 'Contents' in response:
            print(f"\nFiles in {folder} (via direct S3 client):")
            for obj in response['Contents']:
                print(f"  • {obj['Key']} ({obj['Size'] / 1024:.2f} KB)")
        else:
            print(f"No files found in {folder} (via direct S3 client)")

        return True
    except Exception as e:
        print(f"Error listing folder with direct S3 client: {str(e)}")
        return False


def get_presigned_list_url(folder):
    """Generate a presigned URL for listing objects in a folder"""
    url = s3.generate_presigned_url(
        'list_objects_v2',
        Params={
            'Bucket': BUCKET,
            'Prefix': folder
        },
        ExpiresIn=3600
    )
    return url


def try_list_with_presigned_url(url, folder):
    """Try to list objects using a presigned URL"""
    try:
        response = requests.get(url)

        if response.status_code == 200:
            print(f"\nSuccessfully accessed {folder} via presigned URL")
            return True
        else:
            print(f"Failed to access {folder} via presigned URL: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Error accessing folder with presigned URL: {str(e)}")
        return False


def try_read_file_with_policy(policy, folder_to_read):
    """Try to use a policy for one folder to access files in another folder"""
    # First, check if there are any files in the target folder
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET,
            Prefix=folder_to_read
        )

        if 'Contents' not in response or not response['Contents']:
            print(f"No files found in target folder {folder_to_read}")
            return False

        # Get the first file to try to read
        target_file = response['Contents'][0]['Key']
        print(f"Found file to test: {target_file}")

        # Try to get a presigned URL using the policy
        try:
            # Create request with policy fields
            post_data = {
                'key': target_file,  # This is different from the policy folder
                'acl': 'private',
                'AWSAccessKeyId': policy['fields']['AWSAccessKeyId'],
                'policy': policy['fields']['policy'],
                'signature': policy['fields']['signature'],
            }

            # Attempt a POST request to fetch the file
            response = requests.post(
                policy['url'],
                data=post_data
            )

            if response.status_code in [200, 204]:
                print(f"✅ Successfully accessed {target_file} using policy for {policy['folder']}")
                return True
            else:
                print(f"❌ Failed to access {target_file}: {response.status_code}")
                print(response.text)
                return False

        except Exception as e:
            print(f"Error using policy to access file: {str(e)}")
            return False

    except Exception as e:
        print(f"Error listing target folder: {str(e)}")
        return False


def test_cross_folder_access():
    """Test if a policy for one folder can be used to access another folder"""
    print("\n=== Testing Cross-Folder Access ===")

    # First, list files in both folders to verify we have something to test with
    print("\nVerifying folders contain files:")
    policy_folder_has_files = list_files_in_folder(FOLDER_WITH_POLICY)
    target_folder_has_files = list_files_in_folder(FOLDER_TO_ACCESS)

    if not target_folder_has_files:
        print("Target folder is empty, cannot test access")
        return

    # Get policy for policy folder
    policy = get_folder_policy(FOLDER_WITH_POLICY)
    print(f"\nGenerated policy for: {policy['folder']}")

    # Try to directly use the presigned URLs
    print("\nTesting with presigned URLs:")
    url1 = get_presigned_list_url(FOLDER_WITH_POLICY)
    url2 = get_presigned_list_url(FOLDER_TO_ACCESS)

    print(f"Testing access to {FOLDER_WITH_POLICY} with its presigned URL:")
    try_list_with_presigned_url(url1, FOLDER_WITH_POLICY)

    print(f"\nTesting access to {FOLDER_TO_ACCESS} with its presigned URL:")
    try_list_with_presigned_url(url2, FOLDER_TO_ACCESS)

    # Try to read files in target folder using policy for policy folder
    print("\nTesting cross-folder access with policy:")
    print(f"Attempting to use policy for {FOLDER_WITH_POLICY} to access files in {FOLDER_TO_ACCESS}")
    result = try_read_file_with_policy(policy, FOLDER_TO_ACCESS)

    # Summarize the results
    print("\n=== Cross-Folder Access Results ===")
    print(f"Policy folder: {FOLDER_WITH_POLICY}")
    print(f"Target folder: {FOLDER_TO_ACCESS}")
    print(f"Cross-folder access: {'✅ POSSIBLE (SECURITY ISSUE)' if result else '❌ BLOCKED (SECURE)'}")

    # Additional: test download with direct presigned URL
    print("\n=== Testing Direct File Download ===")
    try:
        # Get a file from the target folder
        response = s3.list_objects_v2(
            Bucket=BUCKET,
            Prefix=FOLDER_TO_ACCESS
        )

        if 'Contents' in response and response['Contents']:
            target_file = response['Contents'][0]['Key']

            # Generate direct download URL
            download_url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': BUCKET,
                    'Key': target_file
                },
                ExpiresIn=3600
            )

            print(f"Generated download URL for {target_file}")
            print(f"Testing direct download...")

            # Try to download
            dl_response = requests.get(download_url)
            if dl_response.status_code == 200:
                print(f"✅ Successfully downloaded file with presigned URL")
                print(f"First 100 bytes: {dl_response.content[:100]}")
            else:
                print(f"❌ Failed to download: {dl_response.status_code}")
                print(dl_response.text)
        else:
            print("No files found for download test")
    except Exception as e:
        print(f"Error in download test: {str(e)}")


# Run the test
if __name__ == "__main__":
    test_cross_folder_access()