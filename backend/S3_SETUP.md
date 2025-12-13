# S3 Storage Integration

This project now supports both **local filesystem** and **AWS S3** storage for farm dataset images.

## 📋 Features

- ✅ Toggle between local and S3 storage with a single environment variable
- ✅ Seamless migration with upload script
- ✅ Cost-effective (~₹4/month for 2GB, FREE for first year)
- ✅ No code changes needed in frontend
- ✅ Automatic storage backend initialization

## 🔧 Configuration

### 1. Environment Variables (`.env`)

```env
# Storage Configuration
USE_S3=false                              # Set to 'true' to use S3, 'false' for local
AWS_ACCESS_KEY_ID=your_access_key_here    # Your AWS access key
AWS_SECRET_ACCESS_KEY=your_secret_key     # Your AWS secret key
AWS_REGION=ap-south-1                     # AWS region (default: Mumbai)
S3_BUCKET_NAME=farm-annotation-data       # Your S3 bucket name
```

### 2. Local Storage (Default)

By default, the system uses local filesystem:

```env
USE_S3=false
```

Images are served from `farm_dataset/` directory.

### 3. S3 Storage

To use S3 storage:

```env
USE_S3=true
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-1
S3_BUCKET_NAME=farm-annotation-data
```

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Create AWS Account & S3 Bucket

1. **Sign up for AWS**: https://aws.amazon.com/free/

   - Free tier includes 5 GB storage for 12 months
   - Your 2 GB dataset is FREE for 1 year!

2. **Create S3 Bucket**:

   ```bash
   aws s3 mb s3://farm-annotation-data --region ap-south-1
   ```

   Or via AWS Console:

   - Go to S3 → Create bucket
   - Name: `farm-annotation-data`
   - Region: `Asia Pacific (Mumbai) ap-south-1`
   - Block Public Access: Keep enabled (we use IAM credentials)
   - Click "Create bucket"

3. **Create IAM User** (for access keys):
   - Go to IAM → Users → Add user
   - Username: `farm-annotation-uploader`
   - Access type: Programmatic access
   - Attach policy: `AmazonS3FullAccess` (or create custom policy)
   - Save Access Key ID and Secret Access Key

### Step 3: Update `.env` File

```env
USE_S3=false  # Keep false until upload is complete
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-south-1
S3_BUCKET_NAME=farm-annotation-data
```

### Step 4: Upload Your Dataset to S3

Run the upload script to migrate your local data:

```bash
python upload_to_s3.py
```

The script will:

- ✅ Verify S3 credentials and bucket access
- ✅ Scan your `farm_dataset/` directory
- ✅ Show upload progress with progress bar
- ✅ Skip files that already exist (resume support)
- ✅ Maintain folder structure (farm_id/year/images)

Example output:

```
============================================================
  Farm Dataset S3 Upload Tool
============================================================
✓ Connected to S3 bucket: farm-annotation-data

📦 Found 1247 files to upload

Upload 1247 files to s3://farm-annotation-data/farm_dataset/? (y/n): y

🚀 Uploading files to S3...
100%|████████████████████| 1247/1247 [02:15<00:00, 9.21 files/s]

✅ Upload complete!
   Uploaded: 1247
   Skipped: 0 (already exist)
   Failed: 0

🎉 All files successfully uploaded to S3!
```

### Step 5: Enable S3 Storage

Update your `.env`:

```env
USE_S3=true
```

### Step 6: Restart Backend

```bash
python app.py
```

You should see:

```
🌾 Farm Harvest Annotation Server v3.0 (FastAPI + MongoDB)
🪣 Using S3 storage: farm-annotation-data
💾 Storage: S3
🌐 Starting server at http://localhost:5005
```

## 💰 Cost Breakdown (2 GB Dataset)

### AWS Free Tier (First 12 Months)

- **Storage**: 5 GB FREE
- **Requests**: 20,000 GET, 2,000 PUT FREE
- **Data Transfer**: 100 GB download FREE

**Your Cost: ₹0/month for first year**

### After Free Tier

- **Storage**: 2 GB × ₹1.91 = **₹3.82/month**
- **Requests**: Negligible (~₹0.05)
- **Transfer**: FREE (under 100 GB)

**Your Cost: ~₹4/month (~₹50/year)**

## 🔄 Switching Between Storage Modes

### Switch to S3:

```env
USE_S3=true
```

### Switch back to Local:

```env
USE_S3=false
```

**No code changes needed!** Just restart the backend.

## 📁 S3 Folder Structure

```
s3://farm-annotation-data/
└── farm_dataset/
    ├── 32011568310002/
    │   ├── 2024/
    │   │   ├── Jan_2024_01.png
    │   │   └── Feb_2024_15.png
    │   └── 2025/
    │       └── Mar_2025_10.png
    ├── 32011568310004/
    └── ...
```

## 🛠️ Troubleshooting

### Error: "AWS credentials not found"

**Solution**: Check `.env` file has correct `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

### Error: "S3 bucket not found"

**Solution**: Create bucket with `aws s3 mb s3://farm-annotation-data --region ap-south-1`

### Error: "Access denied to S3 bucket"

**Solution**: Verify IAM user has S3 permissions (attach `AmazonS3FullAccess` policy)

### Slow image loading

**Solution**:

- Use CloudFront CDN for faster delivery
- Enable S3 Transfer Acceleration
- Images are cached for 30 days (see Cache-Control headers)

### Resume interrupted upload

**Solution**: Just run `python upload_to_s3.py` again - it skips existing files

## 🔐 Security Best Practices

1. **Never commit `.env` to git** (already in `.gitignore`)
2. **Use IAM roles** instead of access keys if running on EC2
3. **Enable S3 bucket encryption** (AES-256 or KMS)
4. **Set lifecycle policies** to move old data to Glacier
5. **Enable S3 versioning** for backup/recovery

## 📊 Monitoring

### Check S3 usage:

```bash
aws s3 ls s3://farm-annotation-data --recursive --summarize
```

### Monitor costs:

- AWS Console → Billing Dashboard → S3 costs
- Set up billing alerts in AWS

## 🎯 Architecture

```
Frontend (React)
    ↓ HTTP requests
Backend (FastAPI)
    ↓ Storage abstraction layer
    ├─→ Local Storage (filesystem)
    └─→ S3 Storage (boto3)
```

## 📚 API Endpoints (Unchanged)

All existing endpoints work with both storage backends:

- `GET /api/farms` - List farms
- `GET /api/annotator/farm/{farm_id}` - Get farm images
- `GET /thumbnails/{farm_id}/{filename}` - Serve images
- `GET /thumbs/{farm_id}/{filename}` - Serve thumbnails

**No frontend changes required!**

## ✅ Testing

### Test local storage:

```bash
USE_S3=false python app.py
```

### Test S3 storage:

```bash
USE_S3=true python app.py
```

### Verify in browser:

1. Login to application
2. Navigate to farm images
3. Check browser console for image load times
4. Check backend logs for storage type

## 🚀 Advanced: CloudFront CDN (Optional)

For even faster image delivery:

1. Create CloudFront distribution pointing to S3 bucket
2. Update image URLs to use CloudFront domain
3. Benefit: Global edge caching, faster loads worldwide

Cost: ~₹10/month for 10 GB transfer

## 📞 Support

For issues or questions:

1. Check backend logs for detailed error messages
2. Verify AWS credentials with: `aws s3 ls s3://farm-annotation-data`
3. Test S3 access with: `aws s3 cp test.txt s3://farm-annotation-data/test.txt`

---

**Happy farming! 🌾**
