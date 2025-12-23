"""
FastAPI Farm Harvest Annotation Tool with JWT Auth & MongoDB
Complete system with authentication, admin dashboard, and MongoDB Atlas
Supports both local and S3 storage
"""
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Local imports
from database import (
    connect_to_mongo, 
    close_mongo_connection, 
    get_database,
    USERS_COLLECTION,
    ANNOTATIONS_COLLECTION,
    ASSIGNMENTS_COLLECTION
)
from models import (
    UserCreate, UserResponse, UserInDB,
    AnnotationCreate, AnnotationResponse,
    FarmAssignment,
    Token, LoginRequest
)
from auth import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    decode_access_token
)
from image_utils import parse_date_from_filename
from storage import init_storage, get_storage_instance

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Farm Harvest Annotation Tool API",
    version="3.0",
    description="API with JWT Auth, MongoDB, and Admin Dashboard"
)

# Security
security = HTTPBearer()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Initialize storage backend
storage = None


# Startup/Shutdown Events
@app.on_event("startup")
async def startup_db_client():
    """Connect to MongoDB and initialize storage on startup"""
    global storage
    await connect_to_mongo()
    await initialize_default_admin()
    storage = init_storage()  # Initialize storage backend


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    await close_mongo_connection()


async def initialize_default_admin():
    """Create default admin user if it doesn't exist"""
    db = get_database()
    users_collection = db[USERS_COLLECTION]
    
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    
    existing_admin = await users_collection.find_one({"username": admin_username})
    
    if not existing_admin:
        admin_user = {
            "username": admin_username,
            "email": "admin@farmtool.com",
            "full_name": "Administrator",
            "role": "admin",
            "is_active": True,
            "hashed_password": get_password_hash(admin_password),
            "created_at": datetime.now()
        }
        await users_collection.insert_one(admin_user)
        print(f"[INFO] Default administrator account created: {admin_username}")


# Authentication Dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    role: str = payload.get("role")
    
    if username is None:
        raise credentials_exception
    
    db = get_database()
    user = await db[USERS_COLLECTION].find_one({"username": username})
    
    if user is None:
        raise credentials_exception
    
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "role": user["role"],
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "is_active": user.get("is_active", True)
    }


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role"""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Farm Index and Data Functions
_FARM_INDEX: Optional[List[Dict[str, str]]] = None


def build_farm_index(force: bool = False) -> List[Dict[str, str]]:
    """Build farm index from storage backend"""
    global _FARM_INDEX
    if _FARM_INDEX is not None and not force:
        return _FARM_INDEX
    
    storage_backend = get_storage_instance()
    farm_list = []
    
    try:
        farm_ids = storage_backend.list_farms()
        for farm_id in farm_ids:
            farm_list.append({'farm_id': farm_id})
    except Exception as e:
        print(f"Error building farm index: {e}")
        farm_list = []

    _FARM_INDEX = farm_list
    return _FARM_INDEX


# Build index on startup (after storage is initialized)
# Will be called from startup event


# ============================================================================
# PUBLIC ROUTES (No Auth Required)
# ============================================================================

@app.get("/")
async def index():
    """API documentation"""
    return {
        'name': 'Farm Harvest Annotation Tool API',
        'version': '3.0',
        'description': 'Enterprise-grade farm harvest annotation platform with authentication and assignment management',
        'authentication': {
            'login': 'POST /api/auth/login',
            'current_user': 'GET /api/auth/me'
        },
        'administration': {
            'users': 'GET/POST /api/admin/users',
            'assignments': 'GET/POST /api/admin/assignments',
            'statistics': 'GET /api/admin/stats',
            'export': 'GET /api/admin/download'
        },
        'annotation': {
            'assigned_farms': 'GET /api/annotator/assigned-farms',
            'farm_data': 'GET /api/annotator/farm/{farm_id}',
            'save_annotation': 'POST /api/annotator/save',
            'statistics': 'GET /api/annotator/stats'
        }
    }


@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """Login endpoint - returns JWT token"""
    db = get_database()
    user = await db[USERS_COLLECTION].find_one({"username": login_data.username})
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "role": user["role"],
            "email": user.get("email"),
            "full_name": user.get("full_name")
        }
    }


@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return current_user


# ============================================================================
# ADMIN ROUTES (Admin Only)
# ============================================================================

@app.get("/api/admin/users")
async def get_all_users(admin: dict = Depends(require_admin)):
    """Get all users (admin only)"""
    db = get_database()
    users = await db[USERS_COLLECTION].find().to_list(1000)
    
    return [
        {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user.get("email"),
            "full_name": user.get("full_name"),
            "role": user["role"],
            "is_active": user.get("is_active", True),
            "created_at": user.get("created_at", datetime.now()).isoformat()
        }
        for user in users
    ]


@app.post("/api/admin/users")
async def create_user(user_data: UserCreate, admin: dict = Depends(require_admin)):
    """Create new user (admin only)"""
    db = get_database()
    
    # Check if user already exists
    existing_user = await db[USERS_COLLECTION].find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create new user
    new_user = {
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role,
        "is_active": user_data.is_active,
        "hashed_password": get_password_hash(user_data.password),
        "created_at": datetime.now()
    }
    
    result = await db[USERS_COLLECTION].insert_one(new_user)
    new_user["id"] = str(result.inserted_id)
    
    return {
        "id": new_user["id"],
        "username": new_user["username"],
        "email": new_user.get("email"),
        "full_name": new_user.get("full_name"),
        "role": new_user["role"],
        "created_at": new_user["created_at"].isoformat()
    }


@app.patch("/api/admin/users/{user_id}")
async def update_user(
    user_id: str,
    updates: dict,
    admin: dict = Depends(require_admin)
):
    """Update user (admin only)"""
    db = get_database()
    from bson import ObjectId
    
    # Remove password from updates if present (use separate endpoint)
    if "password" in updates:
        updates["hashed_password"] = get_password_hash(updates.pop("password"))
    
    result = await db[USERS_COLLECTION].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True, "message": "User updated"}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Delete user (admin only)"""
    db = get_database()
    from bson import ObjectId
    
    result = await db[USERS_COLLECTION].delete_one({"_id": ObjectId(user_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True, "message": "User deleted"}


@app.get("/api/admin/assignments")
async def get_all_assignments(admin: dict = Depends(require_admin)):
    """Get all farm assignments (admin only)"""
    db = get_database()
    assignments = await db[ASSIGNMENTS_COLLECTION].find().to_list(1000)
    
    # Get completion stats for each assignment
    result = []
    for assignment in assignments:
        user_id = assignment["user_id"]
        farm_ids = assignment.get("farm_ids", [])
        
        # Count completed annotations
        completed = await db[ANNOTATIONS_COLLECTION].count_documents({
            "user_id": user_id,
            "farm_id": {"$in": farm_ids}
        })
        
        result.append({
            "id": str(assignment["_id"]),
            "user_id": assignment["user_id"],
            "username": assignment["username"],
            "farm_ids": farm_ids,
            "assigned_count": len(farm_ids),
            "completed_count": completed,
            "assigned_at": assignment.get("assigned_at", datetime.now()).isoformat(),
            "status": assignment.get("status", "active")
        })
    
    return result


@app.post("/api/admin/assignments")
async def create_assignment(
    assignment_data: dict,
    admin: dict = Depends(require_admin)
):
    """Create farm assignment or add to existing assignment (admin only)"""
    db = get_database()
    from bson import ObjectId
    
    user_id = assignment_data.get("user_id")
    farm_count = assignment_data.get("farm_count")
    
    # Verify user exists
    user = await db[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all farms
    all_farms = build_farm_index()
    all_farm_ids = [f["farm_id"] for f in all_farms]
    
    # Get already assigned farms
    assignments = await db[ASSIGNMENTS_COLLECTION].find().to_list(1000)
    assigned_farm_ids = set()
    for assignment in assignments:
        assigned_farm_ids.update(assignment.get("farm_ids", []))
    
    # Get unassigned farms
    unassigned_farms = [fid for fid in all_farm_ids if fid not in assigned_farm_ids]
    
    if len(unassigned_farms) < farm_count:
        raise HTTPException(
            status_code=400, 
            detail=f"Only {len(unassigned_farms)} unassigned farms available, but {farm_count} requested"
        )
    
    # Select farms to assign
    farm_ids = unassigned_farms[:farm_count]
    
    # Check if user already has an assignment
    existing_assignment = await db[ASSIGNMENTS_COLLECTION].find_one({"user_id": user_id})
    
    if existing_assignment:
        # Add farms to existing assignment
        updated_farm_ids = existing_assignment.get("farm_ids", []) + farm_ids
        
        await db[ASSIGNMENTS_COLLECTION].update_one(
            {"_id": existing_assignment["_id"]},
            {"$set": {
                "farm_ids": updated_farm_ids,
                "assigned_at": datetime.now()
            }}
        )
        
        return {
            "id": str(existing_assignment["_id"]),
            "user_id": user_id,
            "username": user["username"],
            "farm_ids": updated_farm_ids,
            "assigned_count": len(updated_farm_ids),
            "message": f"Added {len(farm_ids)} farms to existing assignment"
        }
    else:
        # Create new assignment
        new_assignment = {
            "user_id": user_id,
            "username": user["username"],
            "farm_ids": farm_ids,
            "assigned_at": datetime.now(),
            "completed_count": 0,
            "status": "active"
        }
        
        result = await db[ASSIGNMENTS_COLLECTION].insert_one(new_assignment)
        
        return {
            "id": str(result.inserted_id),
            "user_id": user_id,
            "username": user["username"],
            "farm_ids": farm_ids,
            "assigned_count": len(farm_ids),
            "message": f"Created new assignment with {len(farm_ids)} farms"
        }


@app.delete("/api/admin/assignments/{assignment_id}")
async def delete_assignment(assignment_id: str, admin: dict = Depends(require_admin)):
    """Delete assignment (admin only)"""
    db = get_database()
    from bson import ObjectId
    
    result = await db[ASSIGNMENTS_COLLECTION].delete_one({"_id": ObjectId(assignment_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {"success": True, "message": "Assignment deleted"}


@app.delete("/api/admin/annotations/clear")
async def clear_all_annotations(admin: dict = Depends(require_admin)):
    """Clear all annotations (admin only)"""
    db = get_database()
    
    result = await db[ANNOTATIONS_COLLECTION].delete_many({})
    
    return {
        "success": True,
        "message": f"Deleted {result.deleted_count} annotations",
        "deleted_count": result.deleted_count
    }


@app.get("/api/admin/stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    """Get overall statistics (admin only)"""
    db = get_database()
    
    total_users = await db[USERS_COLLECTION].count_documents({"role": "annotator"})
    total_annotations = await db[ANNOTATIONS_COLLECTION].count_documents({})
    total_assignments = await db[ASSIGNMENTS_COLLECTION].count_documents({})
    
    # Get farms count
    farms = build_farm_index()
    total_farms = len(farms)
    
    # Get assigned farms count
    assignments = await db[ASSIGNMENTS_COLLECTION].find().to_list(1000)
    assigned_farms = set()
    for assignment in assignments:
        assigned_farms.update(assignment.get("farm_ids", []))
    
    # Get user stats
    user_stats = []
    users = await db[USERS_COLLECTION].find({"role": "annotator"}).to_list(1000)
    for user in users:
        user_id = str(user["_id"])
        annotations_count = await db[ANNOTATIONS_COLLECTION].count_documents({"user_id": user_id})
        assignment = await db[ASSIGNMENTS_COLLECTION].find_one({"user_id": user_id})
        assigned_count = len(assignment.get("farm_ids", [])) if assignment else 0
        
        user_stats.append({
            "username": user["username"],
            "assigned": assigned_count,
            "completed": annotations_count,
            "progress": round((annotations_count / assigned_count * 100) if assigned_count > 0 else 0, 2)
        })
    
    return {
        "total_users": total_users,
        "total_farms": total_farms,
        "assigned_farms": len(assigned_farms),
        "unassigned_farms": total_farms - len(assigned_farms),
        "total_annotations": total_annotations,
        "total_assignments": total_assignments,
        "user_stats": user_stats
    }


@app.get("/api/admin/download")
async def download_annotations(admin: dict = Depends(require_admin), format: str = Query("csv")):
    """Download all annotations (admin only)"""
    db = get_database()
    annotations = await db[ANNOTATIONS_COLLECTION].find().to_list(10000)
    
    if format == "csv":
        # Create CSV with both 2024 and 2025 selections
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "farm_id", "username", 
            "selected_image_2024", "image_path_2024", "total_images_2024",
            "selected_image_2025", "image_path_2025", "total_images_2025",
            "total_images", "timestamp"
        ])
        
        for annotation in annotations:
            writer.writerow([
                annotation["farm_id"],
                annotation["username"],
                annotation.get("selected_image_2024", ""),
                annotation.get("image_path_2024", ""),
                annotation.get("total_images_2024", ""),
                annotation.get("selected_image_2025", ""),
                annotation.get("image_path_2025", ""),
                annotation.get("total_images_2025", ""),
                annotation.get("total_images", ""),
                annotation.get("timestamp", datetime.now()).isoformat()
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    
    elif format == "json":
        # Return as JSON with both 2024 and 2025 selections
        result = []
        for annotation in annotations:
            result.append({
                "id": str(annotation["_id"]),
                "farm_id": annotation["farm_id"],
                "username": annotation["username"],
                "selected_image_2024": annotation.get("selected_image_2024"),
                "image_path_2024": annotation.get("image_path_2024"),
                "total_images_2024": annotation.get("total_images_2024"),
                "selected_image_2025": annotation.get("selected_image_2025"),
                "image_path_2025": annotation.get("image_path_2025"),
                "total_images_2025": annotation.get("total_images_2025"),
                "total_images": annotation.get("total_images"),
                "timestamp": annotation.get("timestamp", datetime.now()).isoformat()
            })
        
        return result
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'json'")


# ============================================================================
# ANNOTATOR ROUTES (Authenticated Users)
# ============================================================================

@app.get("/api/annotator/assigned-farms")
async def get_assigned_farms(current_user: dict = Depends(get_current_user)):
    """Get farms assigned to current user"""
    db = get_database()
    
    # Get user's assignment
    assignment = await db[ASSIGNMENTS_COLLECTION].find_one({"user_id": current_user["id"]})
    
    if not assignment:
        return {"farm_ids": [], "message": "No farms assigned yet"}
    
    farm_ids = assignment.get("farm_ids", [])
    
    # Get completion status for each farm
    completed_farms = []
    annotations = await db[ANNOTATIONS_COLLECTION].find({
        "user_id": current_user["id"],
        "farm_id": {"$in": farm_ids}
    }).to_list(1000)
    
    completed_farm_ids = [ann["farm_id"] for ann in annotations]
    
    farm_status = []
    for farm_id in farm_ids:
        farm_status.append({
            "farm_id": farm_id,
            "completed": farm_id in completed_farm_ids
        })
    
    return {
        "farm_ids": farm_ids,
        "total_assigned": len(farm_ids),
        "completed_count": len(completed_farm_ids),
        "farms": farm_status
    }


@app.get("/api/annotator/farm/{farm_id}")
async def get_farm_data(farm_id: str, current_user: dict = Depends(get_current_user)):
    """Get farm data for annotation"""
    db = get_database()
    
    # Check if farm is assigned to user
    assignment = await db[ASSIGNMENTS_COLLECTION].find_one({
        "user_id": current_user["id"],
        "farm_ids": farm_id
    })
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This farm is not assigned to you"
        )
    
    # Get farm images
    storage_backend = get_storage_instance()
    
    if not storage_backend.farm_exists(farm_id):
        raise HTTPException(status_code=404, detail="Farm not found")
    
    # Get all image paths from storage
    image_paths = storage_backend.list_images(farm_id)
    
    # Sort by date
    image_data = []
    for img_path in image_paths:
        try:
            # Create a temporary full path for date parsing
            temp_path = f"/{farm_id}/{img_path}"
            date_tuple = parse_date_from_filename(temp_path)
            image_data.append({
                'path': img_path,
                'date': date_tuple
            })
        except Exception:
            # If date parsing fails, add with default date
            image_data.append({
                'path': img_path,
                'date': (1900, 1, 1)
            })
    
    image_data.sort(key=lambda x: x['date'])
    
    # Separate images by year (2024 and 2025)
    thumbnails_2024 = []
    thumbnails_2025 = []
    
    for idx, img_info in enumerate(image_data):
        img_path = img_info['path']
        year, month, day = img_info['date']
        
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        if month > 0:
            date_display = f"{month_names[month]} {day}, {year}" if day > 0 else f"{month_names[month]} {year}"
        else:
            date_display = f"{year}" if year > 1900 else "Unknown"
        
        thumb_data = {
            'index': idx,
            'filename': img_path,
            'date_display': date_display,
            'sort_date': img_info['date'],
            'original_path': img_path
        }
        
        # Group by year
        if year == 2024:
            thumbnails_2024.append(thumb_data)
        elif year == 2025:
            thumbnails_2025.append(thumb_data)
    
    thumbnails_2024.sort(key=lambda x: x['sort_date'])
    thumbnails_2025.sort(key=lambda x: x['sort_date'])
    
    # Reindex thumbnails within each year group
    for idx, thumb in enumerate(thumbnails_2024):
        thumb['index'] = idx
    for idx, thumb in enumerate(thumbnails_2025):
        thumb['index'] = idx
    
    # Check if user has already annotated this farm
    existing_annotation = await db[ANNOTATIONS_COLLECTION].find_one({
        "user_id": current_user["id"],
        "farm_id": farm_id
    })
    
    selected_index_2024 = None
    selected_index_2025 = None
    if existing_annotation:
        # Find index of selected images for each year
        selected_image_2024 = existing_annotation.get("selected_image_2024")
        selected_image_2025 = existing_annotation.get("selected_image_2025")
        
        if selected_image_2024:
            for idx, thumb in enumerate(thumbnails_2024):
                if thumb['filename'] == selected_image_2024:
                    selected_index_2024 = idx
                    break
        
        if selected_image_2025:
            for idx, thumb in enumerate(thumbnails_2025):
                if thumb['filename'] == selected_image_2025:
                    selected_index_2025 = idx
                    break
    
    return {
        'farm_id': farm_id,
        'image_count': len(image_data),
        'thumbnails_2024': thumbnails_2024,
        'thumbnails_2025': thumbnails_2025,
        'selected_index_2024': selected_index_2024,
        'selected_index_2025': selected_index_2025
    }


@app.post("/api/annotator/save")
async def save_annotation(
    annotation_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save annotation with selections for both 2024 and 2025"""
    db = get_database()
    
    farm_id = annotation_data.get("farm_id")
    selected_image_2024 = annotation_data.get("selected_image_2024")
    image_path_2024 = annotation_data.get("image_path_2024")
    selected_image_2025 = annotation_data.get("selected_image_2025")
    image_path_2025 = annotation_data.get("image_path_2025")
    total_images = annotation_data.get("total_images")
    total_images_2024 = annotation_data.get("total_images_2024")
    total_images_2025 = annotation_data.get("total_images_2025")
    
    if not farm_id:
        raise HTTPException(status_code=400, detail="Missing farm_id")
    
    # At least one image should be selected
    if not selected_image_2024 and not selected_image_2025:
        raise HTTPException(status_code=400, detail="At least one image selection is required")
    
    # Check if farm is assigned to user
    assignment = await db[ASSIGNMENTS_COLLECTION].find_one({
        "user_id": current_user["id"],
        "farm_ids": farm_id
    })
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This farm is not assigned to you"
        )
    
    # Save annotation (upsert)
    annotation = {
        "farm_id": farm_id,
        "user_id": current_user["id"],
        "username": current_user["username"],
        "selected_image_2024": selected_image_2024,
        "image_path_2024": image_path_2024,
        "selected_image_2025": selected_image_2025,
        "image_path_2025": image_path_2025,
        "total_images": total_images,
        "total_images_2024": total_images_2024,
        "total_images_2025": total_images_2025,
        "timestamp": datetime.now()
    }
    
    await db[ANNOTATIONS_COLLECTION].update_one(
        {"user_id": current_user["id"], "farm_id": farm_id},
        {"$set": annotation},
        upsert=True
    )
    
    return {
        "success": True,
        "message": f"Annotation saved for farm {farm_id}"
    }


@app.get("/api/annotator/stats")
async def get_annotator_stats(current_user: dict = Depends(get_current_user)):
    """Get current user's annotation statistics"""
    db = get_database()
    
    # Get assignment
    assignment = await db[ASSIGNMENTS_COLLECTION].find_one({"user_id": current_user["id"]})
    assigned_count = len(assignment.get("farm_ids", [])) if assignment else 0
    
    # Get completed count
    completed_count = await db[ANNOTATIONS_COLLECTION].count_documents({
        "user_id": current_user["id"]
    })
    
    progress = round((completed_count / assigned_count * 100) if assigned_count > 0 else 0, 2)
    
    return {
        "username": current_user["username"],
        "assigned": assigned_count,
        "completed": completed_count,
        "remaining": assigned_count - completed_count,
        "progress": progress
    }


# ============================================================================
# IMAGE SERVING ROUTES (Public - No Auth Required)
# ============================================================================

@app.get("/thumbnails/{farm_id}/{filename:path}")
async def serve_image(farm_id: str, filename: str):
    """Serve original images from storage backend"""
    storage_backend = get_storage_instance()
    
    if not storage_backend.farm_exists(farm_id):
        raise HTTPException(status_code=404, detail='Invalid farm id')
    
    if not storage_backend.image_exists(farm_id, filename):
        raise HTTPException(status_code=404, detail='File not found')
    
    try:
        # Get image content from storage
        image_data = storage_backend.get_image(farm_id, filename)
        
        # Return as response
        response = Response(content=image_data, media_type='image/png')
        response.headers["Cache-Control"] = "public, max-age=2592000"
        return response
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='File not found')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error loading image: {str(e)}')


@app.get("/thumbs/{farm_id}/{filename:path}")
async def serve_thumb(farm_id: str, filename: str):
    """Serve thumbnail from storage backend"""
    storage_backend = get_storage_instance()
    
    if not storage_backend.image_exists(farm_id, filename):
        raise HTTPException(status_code=404, detail='File not found')
    
    try:
        # Get image content from storage
        image_data = storage_backend.get_image(farm_id, filename)
        
        # Return as response
        response = Response(content=image_data, media_type='image/png')
        response.headers["Cache-Control"] = "public, max-age=2592000"
        return response
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='File not found')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error loading image: {str(e)}')


if __name__ == '__main__':
    import uvicorn
    
    use_s3 = os.getenv('USE_S3', 'false').lower() == 'true'
    storage_type = "S3" if use_s3 else "Local"
    
    print("="*60)
    print("Farm Harvest Annotation Server v3.0")
    print("="*60)
    print(f"Storage Backend: {storage_type}")
    print(f"Authentication: JWT Enabled")
    print(f"Database: MongoDB Atlas")
    print(f"Server: http://localhost:5005")
    print("="*60)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5005,
        reload=True,
        log_level="info"
    )
