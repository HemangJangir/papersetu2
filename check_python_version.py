#!/usr/bin/env python3
"""
Python Version Check Script for PaperSetu
This script checks if the current Python version is compatible with psycopg3.
"""

import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible with psycopg3"""
    print("🐍 Python Version Compatibility Check")
    print("=" * 50)
    
    # Get current Python version
    current_version = sys.version_info
    print(f"Current Python version: {current_version.major}.{current_version.minor}.{current_version.micro}")
    print(f"Platform: {platform.platform()}")
    
    # Check compatibility
    if current_version.major == 3 and current_version.minor >= 13:
        print("✅ Python 3.13+ detected - Compatible with psycopg3!")
        return True
    elif current_version.major == 3 and current_version.minor == 11:
        print("✅ Python 3.11 detected - Compatible with psycopg3!")
        return True
    elif current_version.major == 3 and current_version.minor == 12:
        print("✅ Python 3.12 detected - Compatible with psycopg3!")
        return True
    else:
        print("⚠️  Python version may have compatibility issues")
        print("   Python 3.11+ is recommended for this project")
        return False

def check_psycopg3_installation():
    """Check if psycopg3 is properly installed"""
    print("\n🔍 Checking psycopg3 installation...")
    
    try:
        import psycopg
        print("✅ psycopg3 imported successfully")
        print(f"   Version: {psycopg.__version__}")
        return True
    except ImportError as e:
        print(f"❌ psycopg3 import failed: {e}")
        print("\n💡 To install psycopg3:")
        print("   pip install psycopg[binary]==3.2.9")
        return False
    except Exception as e:
        print(f"⚠️  psycopg3 import warning: {e}")
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
    
    # Check psycopg3 installation
    psycopg3_ok = check_psycopg3_installation()
    
    # Check Django configuration
    django_ok = check_django_database_config()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    if version_ok and psycopg3_ok and django_ok:
        print("🎉 All checks passed! Your environment is ready for deployment.")
        print("\n💡 For production deployment:")
        print("   1. Ensure requirements.txt contains: psycopg[binary]==3.2.9")
        print("   2. Set DATABASE_URL environment variable in Render")
        print("   3. Python 3.13+ is now supported with psycopg3!")
    else:
        print("❌ Some checks failed. Please address the issues above.")
        print("\n🔧 Quick fixes:")
        if not version_ok:
            print("   - Python 3.11+ is recommended")
        if not psycopg3_ok:
            print("   - Install psycopg3: pip install psycopg[binary]==3.2.9")
        if not django_ok:
            print("   - Check Django settings and database configuration")
        
        sys.exit(1)

if __name__ == "__main__":
    main() 