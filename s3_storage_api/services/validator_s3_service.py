"""
Validator S3 upload service for providing time-limited S3 credentials
"""
import os
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class ValidatorS3Service:
    """
    Service for managing validator S3 upload access and credentials
    """
    
    def __init__(self):
        # S3 Configuration
        self.validator_bucket = os.getenv("S3_VALIDATOR_BUCKET", "resi-validated-data-dev")
        self.s3_region = os.getenv("S3_REGION", "us-east-2")
        self.session_duration = int(os.getenv("VALIDATOR_S3_SESSION_DURATION", "14400"))  # 4 hours
        
        # AWS Configuration
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Validator requirements
        self.min_stake = int(os.getenv("VALIDATOR_MIN_STAKE", "1000"))
        
        # Initialize STS client for temporary credentials
        try:
            self.sts_client = boto3.client(
                'sts',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.s3_region
            )
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.s3_region
            )
        except (NoCredentialsError, Exception) as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            self.sts_client = None
            self.s3_client = None
    
    def generate_validator_folder_path(self, validator_hotkey: str, epoch_id: str) -> str:
        """
        Generate S3 folder path for validator uploads
        """
        return f"validators/{validator_hotkey}/epoch={epoch_id}/"
    
    def create_validator_policy(self, validator_hotkey: str, epoch_id: str) -> Dict:
        """
        Create IAM policy for validator S3 upload access
        """
        folder_path = self.generate_validator_folder_path(validator_hotkey, epoch_id)
        bucket_arn = f"arn:aws:s3:::{self.validator_bucket}"
        
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ValidatorUploadAccess",
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:GetObject",
                        "s3:DeleteObject"
                    ],
                    "Resource": f"{bucket_arn}/{folder_path}*",
                    "Condition": {
                        "StringEquals": {
                            "s3:x-amz-metadata-validator-hotkey": validator_hotkey,
                            "s3:x-amz-metadata-epoch-id": epoch_id
                        }
                    }
                },
                {
                    "Sid": "ValidatorListAccess",
                    "Effect": "Allow", 
                    "Action": [
                        "s3:ListBucket"
                    ],
                    "Resource": bucket_arn,
                    "Condition": {
                        "StringLike": {
                            "s3:prefix": f"{folder_path}*"
                        }
                    }
                }
            ]
        }
        
        return policy
    
    async def generate_temporary_credentials(
        self,
        validator_hotkey: str,
        epoch_id: str,
        purpose: str = "epoch_validation_results"
    ) -> Optional[Dict]:
        """
        Generate temporary AWS credentials for validator S3 upload
        """
        if not self.sts_client:
            logger.error("STS client not initialized - check AWS credentials")
            return None
        
        try:
            # Create session name
            session_name = f"validator-{validator_hotkey[:10]}-{epoch_id}"
            
            # Create policy for this specific validator and epoch
            policy = self.create_validator_policy(validator_hotkey, epoch_id)
            
            # Generate temporary credentials
            response = self.sts_client.assume_role(
                RoleArn=f"arn:aws:iam::{self._get_account_id()}:role/ValidatorS3Role",
                RoleSessionName=session_name,
                Policy=str(policy).replace("'", '"'),  # Convert to JSON string
                DurationSeconds=self.session_duration
            )
            
            credentials = response['Credentials']
            folder_path = self.generate_validator_folder_path(validator_hotkey, epoch_id)
            
            return {
                "success": True,
                "s3_credentials": {
                    "access_key": credentials['AccessKeyId'],
                    "secret_key": credentials['SecretAccessKey'],
                    "session_token": credentials['SessionToken'],
                    "bucket": self.validator_bucket,
                    "region": self.s3_region,
                    "folder_path": folder_path,
                    "expiry": credentials['Expiration'].isoformat()
                },
                "upload_guidelines": {
                    "max_file_size_mb": 100,
                    "allowed_file_types": ["parquet", "json"],
                    "required_metadata": {
                        "validator-hotkey": validator_hotkey,
                        "epoch-id": epoch_id,
                        "upload-purpose": purpose,
                        "upload-timestamp": datetime.utcnow().isoformat()
                    },
                    "folder_structure": folder_path,
                    "example_files": [
                        f"{folder_path}validated_data.parquet",
                        f"{folder_path}validation_report.json", 
                        f"{folder_path}epoch_metadata.json"
                    ]
                }
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                logger.error(f"Access denied for validator S3 credentials: {validator_hotkey}")
                return {
                    "success": False,
                    "error": "access_denied",
                    "message": "Insufficient permissions for S3 access"
                }
            else:
                logger.error(f"AWS error generating validator credentials: {str(e)}")
                return {
                    "success": False,
                    "error": "aws_error",
                    "message": f"AWS service error: {error_code}"
                }
        except Exception as e:
            logger.error(f"Unexpected error generating validator credentials: {str(e)}")
            return {
                "success": False,
                "error": "internal_error",
                "message": "Internal server error"
            }
    
    def _get_account_id(self) -> str:
        """
        Get AWS account ID (simplified - in production, cache this)
        """
        try:
            response = self.sts_client.get_caller_identity()
            return response['Account']
        except Exception:
            # Fallback - you'll need to set this as environment variable
            return os.getenv("AWS_ACCOUNT_ID", "123456789012")
    
    async def generate_presigned_upload_urls(
        self,
        validator_hotkey: str,
        epoch_id: str,
        file_names: list
    ) -> Dict:
        """
        Generate presigned URLs for specific file uploads (alternative to temporary credentials)
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return {"success": False, "error": "s3_client_unavailable"}
        
        folder_path = self.generate_validator_folder_path(validator_hotkey, epoch_id)
        presigned_urls = {}
        
        try:
            for file_name in file_names:
                key = f"{folder_path}{file_name}"
                
                # Generate presigned POST URL
                presigned_post = self.s3_client.generate_presigned_post(
                    Bucket=self.validator_bucket,
                    Key=key,
                    Fields={
                        "x-amz-meta-validator-hotkey": validator_hotkey,
                        "x-amz-meta-epoch-id": epoch_id,
                        "x-amz-meta-upload-timestamp": datetime.utcnow().isoformat()
                    },
                    Conditions=[
                        ["content-length-range", 1024, 104857600],  # 1KB to 100MB
                        {"x-amz-meta-validator-hotkey": validator_hotkey},
                        {"x-amz-meta-epoch-id": epoch_id}
                    ],
                    ExpiresIn=self.session_duration
                )
                
                presigned_urls[file_name] = {
                    "url": presigned_post["url"],
                    "fields": presigned_post["fields"],
                    "key": key
                }
            
            return {
                "success": True,
                "bucket": self.validator_bucket,
                "folder_path": folder_path,
                "presigned_urls": presigned_urls,
                "expires_in_seconds": self.session_duration
            }
            
        except Exception as e:
            logger.error(f"Error generating presigned URLs: {str(e)}")
            return {
                "success": False,
                "error": "presigned_url_error",
                "message": str(e)
            }
    
    async def verify_validator_upload(
        self,
        validator_hotkey: str,
        epoch_id: str,
        file_key: str
    ) -> Dict:
        """
        Verify that a validator upload was successful and has correct metadata
        """
        if not self.s3_client:
            return {"success": False, "error": "s3_client_unavailable"}
        
        try:
            # Check if file exists and get metadata
            response = self.s3_client.head_object(
                Bucket=self.validator_bucket,
                Key=file_key
            )
            
            metadata = response.get('Metadata', {})
            
            # Verify required metadata
            required_metadata = {
                'validator-hotkey': validator_hotkey,
                'epoch-id': epoch_id
            }
            
            missing_metadata = []
            for key, expected_value in required_metadata.items():
                if metadata.get(key) != expected_value:
                    missing_metadata.append(key)
            
            if missing_metadata:
                return {
                    "success": False,
                    "error": "invalid_metadata",
                    "missing_metadata": missing_metadata
                }
            
            return {
                "success": True,
                "file_size": response['ContentLength'],
                "last_modified": response['LastModified'].isoformat(),
                "metadata": metadata
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {
                    "success": False,
                    "error": "file_not_found",
                    "message": f"File {file_key} not found"
                }
            else:
                return {
                    "success": False,
                    "error": "s3_error",
                    "message": str(e)
                }
        except Exception as e:
            return {
                "success": False,
                "error": "verification_error",
                "message": str(e)
            }
    
    async def list_validator_uploads(
        self,
        validator_hotkey: str,
        epoch_id: Optional[str] = None
    ) -> Dict:
        """
        List all uploads for a validator (optionally filtered by epoch)
        """
        if not self.s3_client:
            return {"success": False, "error": "s3_client_unavailable"}
        
        try:
            if epoch_id:
                prefix = self.generate_validator_folder_path(validator_hotkey, epoch_id)
            else:
                prefix = f"validators/{validator_hotkey}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.validator_bucket,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag'].strip('"')
                })
            
            return {
                "success": True,
                "validator_hotkey": validator_hotkey,
                "epoch_id": epoch_id,
                "files": files,
                "total_files": len(files)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "list_error",
                "message": str(e)
            }
    
    async def get_service_health(self) -> Dict:
        """
        Check health of validator S3 service
        """
        health = {
            "validator_s3_service": "unknown",
            "bucket_accessible": False,
            "sts_available": False,
            "configuration": {
                "validator_bucket": self.validator_bucket,
                "s3_region": self.s3_region,
                "session_duration_hours": self.session_duration / 3600,
                "min_validator_stake": self.min_stake
            }
        }
        
        # Check STS availability
        if self.sts_client:
            try:
                self.sts_client.get_caller_identity()
                health["sts_available"] = True
            except Exception as e:
                logger.error(f"STS health check failed: {str(e)}")
        
        # Check S3 bucket accessibility
        if self.s3_client:
            try:
                self.s3_client.head_bucket(Bucket=self.validator_bucket)
                health["bucket_accessible"] = True
            except Exception as e:
                logger.error(f"S3 bucket health check failed: {str(e)}")
        
        # Overall service health
        if health["sts_available"] and health["bucket_accessible"]:
            health["validator_s3_service"] = "healthy"
        elif health["bucket_accessible"]:
            health["validator_s3_service"] = "degraded"  # Can use presigned URLs
        else:
            health["validator_s3_service"] = "unhealthy"
        
        return health
