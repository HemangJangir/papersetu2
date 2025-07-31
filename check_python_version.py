#!/usr/bin/env python3
"""
Python Version Check Script for PaperSetu
This script checks if the current Python version is compatible with psycopg2.
"""

import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible with psycopg2"""
    print("🐍 Python Version Compatibility Check")
    print("=" * 50)
    
    # Get current Python version
    current_version = sys.version_info
    print(f"Current Python version: {current_version.major}.{current_version.minor}.{current_version.micro}")
    print(f"Platform: {platform.platform()}")
    
    # Check compatibility
    if current_version.major == 3 and current_version.minor >= 13:
        print("❌ WARNING: Python 3.13+ detected!")
        print("   psycopg2 is not fully compatible with Python 3.13+")
        print("   This may cause deployment issues on Render.")
        print("\n💡 Recommendations:")
        print("   1. Use Python 3.11.9 for production deployment")
        print("   2. Update runtime.txt to specify python-3.11.9")
        print("   3. Use psycopg2==2.9.9 in requirements.txt")
        return False
    elif current_version.major == 3 and current_version.minor == 11:
        print("✅ Python 3.11 detected - Perfect for psycopg2 compatibility!")
        return True
    elif current_version.major == 3 and current_version.minor == 12:
        print("⚠️  Python 3.12 detected - Should work with psycopg2")
        print("   But Python 3.11.9 is recommended for best compatibility")
        return True
    else:
        print("⚠️  Python version may have compatibility issues")
        print("   Python 3.11.9 is recommended for this project")
        return False

def check_psycopg2_installation():
    """Check if psycopg2 is properly installed"""
    print("\n🔍 Checking psycopg2 installation...")
    
    try:
        import psycopg2
        print("✅ psycopg2 imported successfully")
        print(f"   Version: {psycopg2.__version__}")
        return True
    except ImportError as e:
        print(f"❌ psycopg2 import failed: {e}")
        print("\n💡 To install psycopg2:")
        print("   pip install psycopg2==2.9.9")
        print("   or")
        print("   pip install psycopg2-binary==2.9.9")
        return False
    except Exception as e:
        print(f"⚠️  psycopg2 import warning: {e}")
        return True

def check_django_database_config():
    """Check Django database configuration"""
    print("\n🔍 Checking Django database configuration...")
    
    try:
        import os
        import django
        from pathlib import Path
        
        # Add project directory to path
        project_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(project_dir))
        
        # Set up Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
        django.setup()
        
        from django.conf import settings
        from django.db import connection
        
        # Check database engine
        db_engine = settings.DATABASES['default']['ENGINE']
        print(f"Database Engine: {db_engine}")
        
        if 'postgresql' in db_engine:
            print("✅ PostgreSQL configuration detected")
            if os.environ.get('DATABASE_URL'):
                print("✅ DATABASE_URL environment variable set")
            else:
                print("⚠️  DATABASE_URL not set (using SQLite for development)")
        else:
            print("✅ SQLite configuration detected (development mode)")
        
        # Test database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    print("✅ Database connection successful")
                    return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Django configuration check failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 PaperSetu Python Compatibility Check")
    print("=" * 50)
    
    # Check Python version
    version_ok = check_python_version()
    
    # Check psycopg2 installation
    psycopg2_ok = check_psycopg2_installation()
    
    # Check Django configuration
    django_ok = check_django_database_config()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    if version_ok and psycopg2_ok and django_ok:
        print("🎉 All checks passed! Your environment is ready for deployment.")
        print("\n💡 For production deployment:")
        print("   1. Ensure runtime.txt contains: python-3.11.9")
        print("   2. Ensure requirements.txt contains: psycopg2==2.9.9")
        print("   3. Set DATABASE_URL environment variable in Render")
    else:
        print("❌ Some checks failed. Please address the issues above.")
        print("\n🔧 Quick fixes:")
        if not version_ok:
            print("   - Use Python 3.11.9 for deployment")
        if not psycopg2_ok:
            print("   - Install psycopg2: pip install psycopg2==2.9.9")
        if not django_ok:
            print("   - Check Django settings and database configuration")
        
        sys.exit(1)

if __name__ == "__main__":
    main() 