#!/usr/bin/env python3
"""
Database Configuration Check Script
This script verifies that the database configuration is working correctly.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()

from django.conf import settings
from django.db import connection
from django.core.management import execute_from_command_line

def check_database_configuration():
    """Check database configuration and connectivity"""
    print("🔍 Checking database configuration...")
    
    # Check if we're in production or development
    is_production = os.environ.get('DATABASE_URL') is not None
    
    print(f"Environment: {'Production (Render)' if is_production else 'Development (Local)'}")
    print(f"Database Engine: {settings.DATABASES['default']['ENGINE']}")
    
    if is_production:
        print("✅ Using PostgreSQL (Production)")
        print(f"Database Name: {settings.DATABASES['default'].get('NAME', 'N/A')}")
        print(f"Database Host: {settings.DATABASES['default'].get('HOST', 'N/A')}")
        print(f"Database Port: {settings.DATABASES['default'].get('PORT', 'N/A')}")
    else:
        print("✅ Using SQLite (Development)")
        print(f"Database File: {settings.DATABASES['default']['NAME']}")
    
    # Test database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection test failed")
                return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Check if migrations are applied
    try:
        print("\n🔄 Checking migrations...")
        execute_from_command_line(['manage.py', 'showmigrations', '--list'])
        print("✅ Migration check completed")
    except Exception as e:
        print(f"⚠️  Migration check failed: {e}")
    
    # Check if we can access models
    try:
        from django.contrib.auth import get_user_model
        from conference.models import Conference
        
        User = get_user_model()
        user_count = User.objects.count()
        conference_count = Conference.objects.count()
        
        print(f"\n📊 Database Statistics:")
        print(f"  Users: {user_count}")
        print(f"  Conferences: {conference_count}")
        print("✅ Model access successful")
        
    except Exception as e:
        print(f"❌ Model access failed: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("🚀 PaperSetu Database Configuration Check")
    print("=" * 50)
    
    success = check_database_configuration()
    
    if success:
        print("\n🎉 All database checks passed!")
        print("\n💡 Your database is properly configured and ready to use.")
    else:
        print("\n❌ Database configuration has issues.")
        print("\n🔧 Troubleshooting tips:")
        print("1. For local development: Run 'python setup_local.py'")
        print("2. For production: Check your DATABASE_URL environment variable")
        print("3. Run 'python manage.py migrate' to apply migrations")
        sys.exit(1)

if __name__ == "__main__":
    main() 