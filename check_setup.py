#!/usr/bin/env python3
"""
Quick start script to check if everything is ready to run
Run this before starting the servers to verify configuration
"""
import os
import sys

def check_file_exists(path, description):
    """Check if a file exists"""
    exists = os.path.exists(path)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {path}")
    return exists

def check_env_variable(var_name, env_path):
    """Check if environment variable is set in .env file"""
    if not os.path.exists(env_path):
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
        return var_name in content and not content.split(var_name)[1].split('\n')[0].strip().startswith('=your-')

def main():
    print("\n" + "="*60)
    print("🌾 Farm Annotation Tool - Setup Verification")
    print("="*60 + "\n")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, 'backend')
    frontend_dir = os.path.join(root_dir, 'frontend')
    
    all_good = True
    
    # Check backend files
    print("📦 Backend Files:")
    all_good &= check_file_exists(os.path.join(backend_dir, 'app_new.py'), 'Main FastAPI app')
    all_good &= check_file_exists(os.path.join(backend_dir, 'models.py'), 'Data models')
    all_good &= check_file_exists(os.path.join(backend_dir, 'database.py'), 'Database utilities')
    all_good &= check_file_exists(os.path.join(backend_dir, 'auth.py'), 'Authentication')
    all_good &= check_file_exists(os.path.join(backend_dir, 'requirements.txt'), 'Requirements file')
    print()
    
    # Check environment configuration
    print("⚙️  Configuration:")
    env_path = os.path.join(backend_dir, '.env')
    env_exists = check_file_exists(env_path, 'Environment file (.env)')
    
    if env_exists:
        mongodb_configured = check_env_variable('MONGODB_URL', env_path)
        jwt_configured = check_env_variable('JWT_SECRET_KEY', env_path)
        
        if mongodb_configured:
            print("✓ MongoDB URL configured")
        else:
            print("✗ MongoDB URL not configured (still has placeholder)")
            all_good = False
        
        if jwt_configured:
            print("✓ JWT Secret configured")
        else:
            print("✗ JWT Secret not configured (still has placeholder)")
            all_good = False
    else:
        print("✗ Please create .env file (copy from .env.example)")
        all_good = False
    print()
    
    # Check frontend files
    print("🎨 Frontend Files:")
    all_good &= check_file_exists(os.path.join(frontend_dir, 'components', 'Login.tsx'), 'Login component')
    all_good &= check_file_exists(os.path.join(frontend_dir, 'components', 'AdminDashboard.tsx'), 'Admin dashboard')
    all_good &= check_file_exists(os.path.join(frontend_dir, 'components', 'AnnotatorInterface.tsx'), 'Annotator interface')
    all_good &= check_file_exists(os.path.join(frontend_dir, 'package.json'), 'Package.json')
    print()
    
    # Check data directory
    print("📁 Data Directory:")
    farm_dataset = os.path.join(root_dir, 'farm_dataset')
    dataset_exists = check_file_exists(farm_dataset, 'Farm dataset directory')
    
    if dataset_exists:
        farm_dirs = [d for d in os.listdir(farm_dataset) 
                     if os.path.isdir(os.path.join(farm_dataset, d)) and d != '0']
        print(f"  Found {len(farm_dirs)} farms")
    print()
    
    # Check Python dependencies
    print("🐍 Python Dependencies:")
    try:
        import fastapi
        print("✓ FastAPI installed")
    except ImportError:
        print("✗ FastAPI not installed (run: pip install -r backend/requirements.txt)")
        all_good = False
    
    try:
        import pymongo
        print("✓ PyMongo installed")
    except ImportError:
        print("✗ PyMongo not installed (run: pip install -r backend/requirements.txt)")
        all_good = False
    
    try:
        from jose import jwt
        print("✓ Python-JOSE installed")
    except ImportError:
        print("✗ Python-JOSE not installed (run: pip install -r backend/requirements.txt)")
        all_good = False
    print()
    
    # Final verdict
    print("="*60)
    if all_good:
        print("✅ All checks passed! You're ready to start the servers.")
        print("\nNext steps:")
        print("1. Start backend:  cd backend && python app_new.py")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Open browser:   http://localhost:3000")
        print("4. Login:          admin / admin123")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        print("1. Install Python dependencies: cd backend && pip install -r requirements.txt")
        print("2. Configure .env file: Copy .env.example to .env and update MongoDB URL")
        print("3. Install Node dependencies: cd frontend && npm install")
    print("="*60 + "\n")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
