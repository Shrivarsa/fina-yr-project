import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class S3Service:
    """
    Service for interacting with AWS S3 for storing code content and analysis results.
    
    Environment Variables:
    - AWS_ACCESS_KEY_ID: AWS access key (optional, can use IAM role)
    - AWS_SECRET_ACCESS_KEY: AWS secret key (optional, can use IAM role)
    - AWS_REGION: AWS region (default: us-east-1)
    - S3_BUCKET_NAME: S3 bucket name for storing files
    
    If credentials are not provided, operations will fail gracefully.
    """
    
    def __init__(self):
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        
        self.s3_client = None
        self.enabled = False
        
        if self.bucket_name:
            try:
                if self.aws_access_key and self.aws_secret_key:
                    self.s3_client = boto3.client(
                        's3',
                        aws_access_key_id=self.aws_access_key,
                        aws_secret_access_key=self.aws_secret_key,
                        region_name=self.aws_region
                    )
                else:
                    # Try using default credentials (IAM role, environment, etc.)
                    self.s3_client = boto3.client('s3', region_name=self.aws_region)
                
                # Test connection
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                self.enabled = True
                print(f"[S3Service] Connected to bucket: {self.bucket_name}")
            except (ClientError, NoCredentialsError) as e:
                print(f"[S3Service] S3 not available: {e}. Running without S3 storage.")
                self.enabled = False
        else:
            print("[S3Service] S3_BUCKET_NAME not set. Running without S3 storage.")
    
    def upload_code_content(self, commit_hash: str, code_content: str, user_id: str) -> Optional[str]:
        """
        Upload code content to S3.
        
        Args:
            commit_hash: Unique commit hash identifier
            code_content: The code content to store
            user_id: User ID for organizing files
            
        Returns:
            S3 object key if successful, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            key = f"commits/{user_id}/{commit_hash}.txt"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=code_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'commit_hash': commit_hash,
                    'user_id': user_id
                }
            )
            print(f"[S3Service] Uploaded code content: {key}")
            return key
        except Exception as e:
            print(f"[S3Service] Failed to upload code content: {e}")
            return None
    
    def upload_analysis_result(self, commit_hash: str, analysis_data: dict, user_id: str) -> Optional[str]:
        """
        Upload analysis result JSON to S3.
        
        Args:
            commit_hash: Unique commit hash identifier
            analysis_data: Dictionary containing analysis results
            user_id: User ID for organizing files
            
        Returns:
            S3 object key if successful, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            import json
            key = f"analysis/{user_id}/{commit_hash}.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(analysis_data, indent=2).encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'commit_hash': commit_hash,
                    'user_id': user_id
                }
            )
            print(f"[S3Service] Uploaded analysis result: {key}")
            return key
        except Exception as e:
            print(f"[S3Service] Failed to upload analysis result: {e}")
            return None
    
    def get_code_content(self, commit_hash: str, user_id: str) -> Optional[str]:
        """
        Retrieve code content from S3.
        
        Args:
            commit_hash: Unique commit hash identifier
            user_id: User ID for organizing files
            
        Returns:
            Code content as string if found, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            key = f"commits/{user_id}/{commit_hash}.txt"
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            print(f"[S3Service] Retrieved code content: {key}")
            return content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                print(f"[S3Service] Code content not found: {key}")
            else:
                print(f"[S3Service] Failed to retrieve code content: {e}")
            return None
        except Exception as e:
            print(f"[S3Service] Error retrieving code content: {e}")
            return None
    
    def is_enabled(self) -> bool:
        """Check if S3 service is enabled and available."""
        return self.enabled
