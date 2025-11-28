"""
MongoDB database connection and utilities
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "farm_annotations"

# Global database client
client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    """Connect to MongoDB"""
    global client, database
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        database = client[DATABASE_NAME]
        # Test connection
        await client.admin.command('ping')
        print(f"✓ Connected to MongoDB: {DATABASE_NAME}")
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✓ MongoDB connection closed")


def get_database():
    """Get database instance"""
    return database


# Collection names
USERS_COLLECTION = "users"
ANNOTATIONS_COLLECTION = "annotations"
ASSIGNMENTS_COLLECTION = "assignments"
