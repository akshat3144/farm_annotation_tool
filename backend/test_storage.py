"""
Test storage configuration
Verifies that storage backend is properly configured
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def test_storage():
    """Test storage configuration"""
    print("=" * 60)
    print("  Storage Configuration Test")
    print("=" * 60)
    print()
    
    use_s3 = os.getenv('USE_S3', 'false').lower() == 'true'
    
    print(f"📋 Configuration:")
    print(f"   USE_S3: {os.getenv('USE_S3', 'false')}")
    print(f"   Storage Mode: {'S3' if use_s3 else 'Local'}")
    print()
    
    if use_s3:
        # Test S3 configuration
        print("🔍 Checking S3 configuration...")
        print()
        
        bucket_name = os.getenv('S3_BUCKET_NAME')
        region = os.getenv('AWS_REGION', 'ap-south-1')
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        missing = []
        if not bucket_name:
            missing.append('S3_BUCKET_NAME')
        if not access_key:
            missing.append('AWS_ACCESS_KEY_ID')
        if not secret_key:
            missing.append('AWS_SECRET_ACCESS_KEY')
        
        if missing:
            print(f"❌ Missing configuration:")
            for var in missing:
                print(f"   - {var}")
            print()
            print("💡 Add these to your .env file")
            return False
        
        print(f"✅ Configuration found:")
        print(f"   Bucket: {bucket_name}")
        print(f"   Region: {region}")
        print(f"   Access Key: {access_key[:8]}..." if access_key else "   Access Key: Not set")
        print()
        
        # Test S3 connection
        print("🔌 Testing S3 connection...")
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
            
            # Test bucket access
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Successfully connected to S3 bucket: {bucket_name}")
            print()
            
            # List some objects
            print("📦 Checking bucket contents...")
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix='farm_dataset/',
                MaxKeys=5
            )
            
            if 'Contents' in response:
                print(f"✅ Found {response.get('KeyCount', 0)} items (showing first 5):")
                for obj in response['Contents'][:5]:
                    print(f"   - {obj['Key']}")
                print()
            else:
                print("⚠️  No files found in bucket")
                print("   Run 'python upload_to_s3.py' to upload your dataset")
                print()
            
            return True
            
        except ImportError:
            print("❌ boto3 not installed")
            print("   Run: pip install boto3")
            return False
        except NoCredentialsError:
            print("❌ Invalid AWS credentials")
            print("   Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
            return False
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"❌ S3 bucket not found: {bucket_name}")
                print(f"   Create it with: aws s3 mb s3://{bucket_name} --region {region}")
            elif error_code == '403':
                print(f"❌ Access denied to bucket: {bucket_name}")
                print("   Check IAM permissions")
            else:
                print(f"❌ S3 error: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return False
    
    else:
        # Test local storage
        print("🔍 Checking local storage...")
        print()
        
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dataset_dir = os.path.join(root_dir, "farm_dataset")
        
        print(f"📁 Dataset directory: {dataset_dir}")
        
        if not os.path.exists(dataset_dir):
            print(f"❌ Directory not found!")
            print(f"   Create it or check the path")
            return False
        
        print(f"✅ Directory exists")
        print()
        
        # Count farms
        try:
            farms = [
                d for d in os.listdir(dataset_dir)
                if os.path.isdir(os.path.join(dataset_dir, d)) and d != "0"
            ]
            print(f"📊 Found {len(farms)} farms")
            if farms:
                print(f"   Sample farms: {', '.join(farms[:5])}")
                if len(farms) > 5:
                    print(f"   ... and {len(farms) - 5} more")
            print()
            
            # Count total images
            total_images = 0
            for farm in farms[:10]:  # Check first 10 farms
                farm_path = os.path.join(dataset_dir, farm)
                for root, dirs, files in os.walk(farm_path):
                    total_images += sum(1 for f in files if f.lower().endswith(('.tif', '.tiff', '.png', '.jpg')))
            
            if total_images > 0:
                print(f"📸 Sample: Found {total_images} images in first {min(len(farms), 10)} farms")
            print()
            
            return True
            
        except Exception as e:
            print(f"❌ Error reading directory: {str(e)}")
            return False


def main():
    success = test_storage()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Storage configuration is valid!")
        print()
        print("Next steps:")
        if os.getenv('USE_S3', 'false').lower() == 'true':
            print("1. Run: python app.py")
            print("2. Backend will use S3 storage")
        else:
            print("1. To use S3: Set USE_S3=true in .env")
            print("2. Run: python upload_to_s3.py (to migrate data)")
            print("3. Run: python app.py")
    else:
        print("❌ Storage configuration has issues")
        print()
        print("See errors above for details")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
