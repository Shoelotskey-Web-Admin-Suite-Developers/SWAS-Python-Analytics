#!/usr/bin/env python3
"""
test_environment.py

Quick test script to verify the Python environment is set up correctly on Render.
This can be used to debug any environment issues before running the full analytics pipeline.
"""

import sys
import os
from datetime import datetime

def test_python_environment():
    """Test the Python environment and key dependencies"""
    print("🔍 Testing Python Environment")
    print("=" * 50)
    
    # Python version
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Test Time: {datetime.now()}")
    
    # Test key imports
    test_imports = [
        'pandas',
        'numpy', 
        'pymongo',
        'matplotlib',
        'prophet',
        'python-dotenv'
    ]
    
    print("\n📦 Testing Package Imports:")
    print("-" * 30)
    
    for package in test_imports:
        try:
            if package == 'python-dotenv':
                import dotenv
                print(f"✅ {package}: {dotenv.__version__}")
            else:
                module = __import__(package)
                version = getattr(module, '__version__', 'Unknown')
                print(f"✅ {package}: {version}")
        except ImportError as e:
            print(f"❌ {package}: Import Error - {e}")
        except Exception as e:
            print(f"⚠️  {package}: {e}")
    
    # Test environment variables
    print("\n🔧 Environment Variables:")
    print("-" * 30)
    env_vars = ['PYTHONPATH', 'DATABASE_URL', 'MONGODB_URI']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive data
            if 'password' in value.lower() or 'mongodb' in value.lower():
                masked = value[:10] + "***" + value[-10:] if len(value) > 20 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
    
    print("\n" + "=" * 50)
    print("✅ Environment test completed!")
    return True

if __name__ == "__main__":
    try:
        test_python_environment()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        sys.exit(1)