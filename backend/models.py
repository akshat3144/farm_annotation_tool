"""
Database models for Farm Annotation Tool
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserBase(BaseModel):
    """Base user model"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "annotator"  # "admin" or "annotator"
    is_active: bool = True


class UserCreate(UserBase):
    """User creation model"""
    password: str


class UserInDB(UserBase):
    """User model in database"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserResponse(UserBase):
    """User response model"""
    id: str = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class FarmAssignment(BaseModel):
    """Farm assignment model"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    username: str
    farm_ids: List[str]
    assigned_at: datetime = Field(default_factory=datetime.now)
    completed_count: int = 0
    status: str = "active"  # "active", "completed", "inactive"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class AnnotationBase(BaseModel):
    """Base annotation model"""
    farm_id: str
    user_id: str
    username: str
    # Updated to support 2 images: one from 2024, one from 2025
    selected_image_2024: Optional[str] = None
    image_path_2024: Optional[str] = None
    selected_image_2025: Optional[str] = None
    image_path_2025: Optional[str] = None
    total_images: Optional[int] = None
    total_images_2024: Optional[int] = None
    total_images_2025: Optional[int] = None


class AnnotationCreate(AnnotationBase):
    """Annotation creation model"""
    pass


class AnnotationInDB(AnnotationBase):
    """Annotation model in database"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


class AnnotationResponse(AnnotationBase):
    """Annotation response model"""
    id: str = Field(alias="_id")
    timestamp: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class Token(BaseModel):
    """JWT token model"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str
