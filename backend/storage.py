"""
Storage abstraction layer for local and S3 storage
Provides unified interface for file operations
"""
import os
import io
from typing import List, Tuple, Optional, BinaryIO
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

load_dotenv()


class StorageBackend:
    """Abstract base for storage backends"""
    
    def list_farms(self) -> List[str]:
        """List all farm IDs"""
        raise NotImplementedError
    
    def list_images(self, farm_id: str) -> List[str]:
        """List all images for a farm (relative paths)"""
        raise NotImplementedError
    
    def get_image(self, farm_id: str, image_path: str) -> bytes:
        """Get image file content"""
        raise NotImplementedError
    
    def farm_exists(self, farm_id: str) -> bool:
        """Check if farm exists"""
        raise NotImplementedError
    
    def image_exists(self, farm_id: str, image_path: str) -> bool:
        """Check if image exists"""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        if not os.path.exists(base_path):
            raise ValueError(f"Base path does not exist: {base_path}")
    
    def list_farms(self) -> List[str]:
        """List all farm directories"""
        try:
            farms = [
                d for d in os.listdir(self.base_path)
                if os.path.isdir(os.path.join(self.base_path, d)) and d != "0"
            ]
            return sorted(farms)
        except Exception as e:
            print(f"Error listing farms: {e}")
            return []
    
    def list_images(self, farm_id: str) -> List[str]:
        """List all images in farm directory (recursively)"""
        farm_path = os.path.join(self.base_path, farm_id)
        if not os.path.isdir(farm_path):
            return []
        
        images = []
        for root, dirs, files in os.walk(farm_path):
            for f in files:
                if f.lower().endswith(('.tif', '.tiff', '.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(root, f)
                    # Get relative path from farm directory
                    rel_path = os.path.relpath(full_path, farm_path)
                    images.append(rel_path.replace('\\', '/'))
        
        return images
    
    def get_image(self, farm_id: str, image_path: str) -> bytes:
        """Read image file"""
        full_path = os.path.join(self.base_path, farm_id, image_path)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    def farm_exists(self, farm_id: str) -> bool:
        """Check if farm directory exists"""
        return os.path.isdir(os.path.join(self.base_path, farm_id))
    
    def image_exists(self, farm_id: str, image_path: str) -> bool:
        """Check if image file exists"""
        full_path = os.path.join(self.base_path, farm_id, image_path)
        return os.path.isfile(full_path)


class S3Storage(StorageBackend):
    """AWS S3 storage"""
    
    def __init__(self, bucket_name: str, region: str = 'ap-south-1', prefix: str = 'farm_dataset/'):
        self.bucket_name = bucket_name
        self.region = region
        self.prefix = prefix
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            
            # Test connection
            self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Connected to S3 bucket: {bucket_name}")
            
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ValueError(f"S3 bucket not found: {bucket_name}")
            elif error_code == '403':
                raise ValueError(f"Access denied to S3 bucket: {bucket_name}")
            else:
                raise ValueError(f"S3 connection error: {str(e)}")
    
    def list_farms(self) -> List[str]:
        """List all farm folders in S3"""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            farms = set()
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix, Delimiter='/'):
                # Get common prefixes (directories)
                for prefix in page.get('CommonPrefixes', []):
                    farm_path = prefix['Prefix']
                    farm_id = farm_path[len(self.prefix):].rstrip('/')
                    if farm_id and farm_id != '0':
                        farms.add(farm_id)
            
            return sorted(list(farms))
        except Exception as e:
            print(f"Error listing farms from S3: {e}")
            return []
    
    def list_images(self, farm_id: str) -> List[str]:
        """List all images for a farm in S3"""
        try:
            farm_prefix = f"{self.prefix}{farm_id}/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            images = []
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=farm_prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    # Check if it's an image file
                    if key.lower().endswith(('.tif', '.tiff', '.png', '.jpg', '.jpeg')):
                        # Get relative path from farm directory
                        rel_path = key[len(farm_prefix):]
                        images.append(rel_path)
            
            return images
        except Exception as e:
            print(f"Error listing images from S3: {e}")
            return []
    
    def get_image(self, farm_id: str, image_path: str) -> bytes:
        """Download image from S3"""
        try:
            key = f"{self.prefix}{farm_id}/{image_path}"
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"Image not found in S3: {image_path}")
            raise
    
    def farm_exists(self, farm_id: str) -> bool:
        """Check if farm exists in S3"""
        try:
            farm_prefix = f"{self.prefix}{farm_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=farm_prefix,
                MaxKeys=1
            )
            return 'Contents' in response and len(response['Contents']) > 0
        except Exception:
            return False
    
    def image_exists(self, farm_id: str, image_path: str) -> bool:
        """Check if image exists in S3"""
        try:
            key = f"{self.prefix}{farm_id}/{image_path}"
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False


def get_storage() -> StorageBackend:
    """Factory function to get appropriate storage backend"""
    use_s3 = os.getenv('USE_S3', 'false').lower() == 'true'
    
    if use_s3:
        bucket_name = os.getenv('S3_BUCKET_NAME')
        region = os.getenv('AWS_REGION', 'ap-south-1')
        
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME not set in environment variables")
        
        print(f"🪣 Using S3 storage: {bucket_name}")
        return S3Storage(bucket_name, region)
    else:
        # Use local storage
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        farm_dataset_dir = os.path.join(root_dir, "farm_dataset")
        
        print(f"📁 Using local storage: {farm_dataset_dir}")
        return LocalStorage(farm_dataset_dir)


# Global storage instance
_storage: Optional[StorageBackend] = None


def init_storage():
    """Initialize storage backend"""
    global _storage
    _storage = get_storage()
    return _storage


def get_storage_instance() -> StorageBackend:
    """Get initialized storage instance"""
    if _storage is None:
        init_storage()
    return _storage
