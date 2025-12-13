# Farm Harvest Annotation Tool

A modern web-based tool for annotating farm harvest images with temporal image selection. This project features a Next.js frontend and a FastAPI backend with **flexible storage options** (local or AWS S3), supporting large-scale annotation workflows with JWT authentication and MongoDB.

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Configure storage (optional - defaults to local)
# Edit .env to set USE_S3=true for AWS S3 storage

python app.py
```

Backend runs on `http://localhost:5005`

**Storage Options:**

- **Local Storage** (default): Uses `farm_dataset/` directory
- **AWS S3**: Toggle with `USE_S3=true` in `.env` - See [S3_SETUP.md](backend/S3_SETUP.md)

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`

---

## 📁 Project Structure

```
CNH/
├── backend/               # FastAPI backend
│   ├── app.py             # Main application with storage abstraction
│   ├── storage.py         # Storage layer (Local/S3)
│   ├── database.py        # MongoDB integration
│   ├── auth.py            # JWT authentication
│   ├── models.py          # Data models
│   ├── upload_to_s3.py    # S3 migration tool
│   ├── test_storage.py    # Storage configuration tester
│   ├── S3_SETUP.md        # Complete S3 setup guide
│   ├── requirements.txt   # Python dependencies
│   └── .env               # Environment configuration
├── frontend/             # Next.js frontend
│   ├── app/              # Next.js app directory
│   ├── components/       # React components
│   ├── public/           # Static assets
│   └── package.json      # Node dependencies
├── farm_dataset/         # Farm images (local storage)
└── ...
```

---

## ✨ Features

### Core Features

- **Image Annotation**: Select harvest-ready images from a temporal timeline
- **Navigation**: Browse through farms with keyboard shortcuts or buttons
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Real-time Updates**: Instant feedback on save/skip actions
- **Session Management**: Save progress and reset as needed

### Storage & Performance

- **🆕 Flexible Storage**: Toggle between local filesystem and AWS S3
  - Local storage for development/testing
  - S3 for production with ~₹4/month for 2GB (FREE first year)
  - See [S3_SETUP.md](backend/S3_SETUP.md) for details
- **Preloading**: Optimized image loading for smooth navigation
- **Image Caching**: 30-day cache headers for better performance

### Authentication & User Management

- **JWT Authentication**: Secure token-based authentication
- **Role-based Access**: Admin and annotator roles
- **User Dashboard**: Track assigned farms and progress
- **Batch Assignment**: Admins can assign farm batches to users

### Database

- **MongoDB Atlas**: Cloud-based document storage
- **User Management**: Complete CRUD operations
- **Farm Assignments**: Track which farms are assigned to which users
- **Annotations**: Store all annotation history

---

## 🎮 Usage

1. **View Farm Images**: Images are displayed in a grid showing the 12-month timeline
2. **Select Image**: Click on an image to mark it as harvest-ready
3. **Save**: Click "Save Selection" or press `Enter` to record your annotation
4. **Navigate**: Use Previous/Next buttons or arrow keys
5. **Skip**: Skip farms without selection if needed

---

## 🔧 Configuration

### Backend Configuration

**Environment Variables (`.env`):**

```env
# MongoDB
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/db

# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Admin Configuration
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123

# Storage Configuration
USE_S3=false                              # Set to 'true' for AWS S3
AWS_ACCESS_KEY_ID=your_access_key         # Required for S3
AWS_SECRET_ACCESS_KEY=your_secret_key     # Required for S3
AWS_REGION=ap-south-1                     # AWS region
S3_BUCKET_NAME=farm-annotation-data       # S3 bucket name
```

**Storage Options:**

- **Local (default)**: Set `USE_S3=false` - uses `farm_dataset/` directory
- **AWS S3**: Set `USE_S3=true` - stores images in S3 bucket
  - Cost: ~₹4/month for 2GB (FREE first year with AWS Free Tier)
  - See [S3_SETUP.md](backend/S3_SETUP.md) for complete setup guide

**Test Your Configuration:**

```bash
cd backend
python test_storage.py  # Verify storage is properly configured
```

### Frontend Configuration

- Edit `frontend/.env` for API URL and environment variables
- Next.js rewrites proxy API requests to the backend automatically

---

## 🌐 API Endpoints

### Authentication

- `POST /api/auth/login` - User login with JWT token generation
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### User Management (Admin)

- `GET /api/admin/users` - List all users
- `POST /api/admin/users` - Create new user
- `PUT /api/admin/users/{id}` - Update user
- `DELETE /api/admin/users/{id}` - Delete user

### Farm Management

- `GET /api/farms` - List all farms
- `GET /api/annotator/farm/{id}` - Get farm images and data
- `GET /api/annotator/my-farms` - Get farms assigned to current user

### Assignments (Admin)

- `POST /api/admin/assignments` - Assign farms to users
- `GET /api/admin/assignments` - List all assignments
- `DELETE /api/admin/assignments/{id}` - Delete assignment

### Annotations

- `POST /api/annotator/save` - Save annotation
- `GET /api/admin/annotations` - Get all annotations (admin)
- `GET /api/admin/export/csv` - Export annotations as CSV
- `GET /api/admin/export/json` - Export annotations as JSON

### Image Serving (Public)

- `GET /thumbnails/{farm_id}/{filename}` - Serve farm images
- `GET /thumbs/{farm_id}/{filename}` - Serve thumbnails

**Note**: All images are served from the configured storage backend (Local or S3)

---

## 💾 Data Storage

### Annotations

All annotations are stored in MongoDB Atlas with the following structure:

```javascript
{
  user_id: "user_id",
  farm_id: "32011568310002",
  selected_image: "2024/Dec_2024_05.png",
  image_path: "2024/Dec_2024_05.png",
  total_images: 12,
  timestamp: ISODate("2025-12-13T14:30:00Z")
}
```

### Farm Images

Images can be stored in two ways:

**1. Local Storage (default)**

- Location: `farm_dataset/{farm_id}/{year}/{image_file}`
- Example: `farm_dataset/32011568310002/2024/Dec_2024_05.png`
- Best for: Development, small datasets, no internet required

**2. AWS S3 Storage**

- Location: `s3://{bucket_name}/farm_dataset/{farm_id}/{year}/{image_file}`
- Cost: ~₹4/month for 2GB (FREE first year)
- Best for: Production, scalability, global access
- Setup guide: [S3_SETUP.md](backend/S3_SETUP.md)

**Migrating to S3:**

```bash
# Configure .env with AWS credentials
python upload_to_s3.py  # Upload all local data to S3
# Set USE_S3=true in .env
python app.py  # Restart backend
```

---

## 📦 Technologies

### Backend

- **FastAPI** 0.104+ - Modern Python web framework
- **Motor** - Async MongoDB driver
- **MongoDB Atlas** - Cloud database
- **JWT** - Token-based authentication
- **Boto3** - AWS SDK for S3 integration
- **Pillow** - Image processing
- **Python** 3.8+

### Frontend

- **Next.js** 16 - React framework
- **React** 19 - UI library
- **TypeScript** 5 - Type safety
- **CSS Modules** - Scoped styling

### Storage

- **Local Filesystem** - Default storage
- **AWS S3** - Optional cloud storage
  - Intelligent Tiering for cost optimization
  - 30-day cache headers
  - CloudFront CDN support (optional)

### Database

- **MongoDB Atlas** - Document database
  - User management
  - Annotations storage
  - Farm assignments

---

## 🛠️ Advanced Features

### Storage Flexibility

- **Storage Abstraction Layer**: Unified API for local and S3 storage
- **Zero-downtime Migration**: Upload to S3 while keeping local storage
- **Cost Monitoring**: Built-in S3 cost calculator and usage tracking
- **Resume Support**: Interrupted uploads can be resumed

### Authentication & Security

- **JWT Tokens**: Secure, stateless authentication
- **Role-based Access Control**: Admin vs annotator permissions
- **Password Hashing**: Bcrypt for secure password storage
- **Token Expiration**: Configurable session duration

### Database

- **MongoDB Atlas**: Cloud-hosted, scalable NoSQL database
- **Async Operations**: Non-blocking database queries
- **Connection Pooling**: Efficient connection management

### Performance

- **Image Caching**: 30-day browser cache for images
- **Preloading**: Next/previous farm preloading
- **Optimized Queries**: Indexed database queries
- **Pagination**: Efficient data retrieval

### Administration

- **User Management**: Create, update, delete users
- **Farm Assignment**: Assign specific farms to users
- **Progress Tracking**: Monitor annotation completion
- **Data Export**: CSV and JSON export formats

### Deployment

- **Production Ready**: Uvicorn ASGI server
- **CORS Configured**: Frontend-backend communication enabled
- **Environment Variables**: Secure configuration management
- **Logging**: Comprehensive error and access logging

---

## 🐛 Troubleshooting

### Storage Issues

**Images not loading:**

```bash
# Test your storage configuration
python test_storage.py

# For local storage: Check farm_dataset directory exists
# For S3: Verify AWS credentials and bucket access
```

**S3 connection errors:**

- Check AWS credentials in `.env`
- Verify S3 bucket exists and is accessible
- Test with: `aws s3 ls s3://your-bucket-name`
- See [S3_SETUP.md](backend/S3_SETUP.md) troubleshooting section

### Authentication Issues

**Login fails:**

- Verify MongoDB connection in `.env`
- Check default admin credentials
- Reset password in MongoDB directly if needed

**Token expired:**

- Tokens expire after configured time (default: 7 days)
- Users need to log in again

### CORS Errors

**Frontend can't reach backend:**

- Ensure backend is running on `http://localhost:5005`
- Check CORS configuration in `app.py`
- Verify frontend API URL in `.env`

### Database Connection

**MongoDB connection fails:**

- Verify `MONGODB_URL` in `.env`
- Check MongoDB Atlas IP whitelist (allow 0.0.0.0/0 for testing)
- Ensure network access in MongoDB Atlas settings

### Port Already in Use

**Backend port conflict:**

```bash
# Change port in app.py or run with:
python app.py  # Uses port 5005 by default
```

**Frontend port conflict:**

```bash
npm run dev -- -p 3001  # Use different port
```

### Performance Issues

**Slow image loading:**

- For local: Check disk I/O performance
- For S3: Consider CloudFront CDN
- Enable browser cache (Cache-Control headers already set)
- Check network bandwidth
