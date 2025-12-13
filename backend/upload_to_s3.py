"""
Upload farm dataset from local storage to S3
Run this script to migrate your data to AWS S3
"""
import os
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


def upload_to_s3():
    """Upload all farm data to S3"""
    
    # Get configuration
    bucket_name = os.getenv('S3_BUCKET_NAME')
    region = os.getenv('AWS_REGION', 'ap-south-1')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if not all([bucket_name, access_key, secret_key]):
        print("❌ Error: Missing S3 configuration in .env file")
        print("Required: S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        return False
    
    # Get local dataset path
    root_dir = Path(__file__).parent.parent
    dataset_dir = root_dir / "farm_dataset"
    
    if not dataset_dir.exists():
        print(f"❌ Error: Dataset directory not found: {dataset_dir}")
        return False
    
    # Initialize S3 client
    try:
        s3_client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # Test connection
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ Connected to S3 bucket: {bucket_name}")
        
    except NoCredentialsError:
        print("❌ Error: Invalid AWS credentials")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"❌ Error: S3 bucket not found: {bucket_name}")
            print(f"Create it with: aws s3 mb s3://{bucket_name} --region {region}")
        elif error_code == '403':
            print(f"❌ Error: Access denied to bucket: {bucket_name}")
        else:
            print(f"❌ Error: {str(e)}")
        return False
    
    # Collect all files to upload
    files_to_upload = []
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            if file.lower().endswith(('.tif', '.tiff', '.png', '.jpg', '.jpeg')):
                local_path = Path(root) / file
                rel_path = local_path.relative_to(dataset_dir)
                files_to_upload.append((local_path, rel_path))
    
    if not files_to_upload:
        print("❌ No image files found in dataset directory")
        return False
    
    print(f"\n📦 Found {len(files_to_upload)} files to upload")
    
    # Confirm upload
    response = input(f"\nUpload {len(files_to_upload)} files to s3://{bucket_name}/farm_dataset/? (y/n): ")
    if response.lower() != 'y':
        print("Upload cancelled")
        return False
    
    # Upload files with progress bar
    uploaded = 0
    failed = 0
    skipped = 0
    
    print("\n🚀 Uploading files to S3...")
    
    with tqdm(total=len(files_to_upload), unit='file') as pbar:
        for local_path, rel_path in files_to_upload:
            s3_key = f"farm_dataset/{rel_path.as_posix()}"
            
            try:
                # Check if file already exists
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                    # File exists, check size
                    local_size = local_path.stat().st_size
                    s3_obj = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                    s3_size = s3_obj['ContentLength']
                    
                    if local_size == s3_size:
                        skipped += 1
                        pbar.set_description(f"Skipped: {rel_path.name}")
                        pbar.update(1)
                        continue
                except ClientError:
                    pass  # File doesn't exist, upload it
                
                # Upload file
                s3_client.upload_file(
                    str(local_path),
                    bucket_name,
                    s3_key,
                    ExtraArgs={'ContentType': 'image/png' if str(local_path).endswith('.png') else 'image/tiff'}
                )
                uploaded += 1
                pbar.set_description(f"Uploaded: {rel_path.name}")
                
            except Exception as e:
                failed += 1
                pbar.set_description(f"Failed: {rel_path.name}")
                print(f"\n❌ Failed to upload {rel_path}: {str(e)}")
            
            pbar.update(1)
    
    # Summary
    print(f"\n✅ Upload complete!")
    print(f"   Uploaded: {uploaded}")
    print(f"   Skipped: {skipped} (already exist)")
    print(f"   Failed: {failed}")
    
    if failed == 0:
        print(f"\n🎉 All files successfully uploaded to S3!")
        print(f"\nNext steps:")
        print(f"1. Update .env: SET USE_S3=true")
        print(f"2. Restart your backend server")
    
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("  Farm Dataset S3 Upload Tool")
    print("=" * 60)
    
    success = upload_to_s3()
    sys.exit(0 if success else 1)
