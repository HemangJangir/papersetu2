#!/usr/bin/env python3
"""
Quick Migration Fix for Render
Run this script on Render to fix the accounts_user table issue immediately.
"""

import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection

def main():
    print("🚀 Quick Migration Fix for Render")
    print("=" * 40)
    
    # Check if we're in production
    is_production = os.environ.get('DATABASE_URL') is not None
    print(f"Environment: {'Production (PostgreSQL)' if is_production else 'Development (SQLite)'}")
    
    # Test database connection
    print("\n🔍 Testing database connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection test failed")
                return
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Run migrations
    print("\n🔄 Running migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate', '--no-input'])
        print("✅ Migrations completed successfully")
    except Exception as e:
        print(f"⚠️  Normal migration failed: {e}")
        print("🔄 Trying with fake initial...")
        try:
            execute_from_command_line(['manage.py', 'migrate', '--fake-initial', '--no-input'])
            print("✅ Migrations completed with fake initial")
        except Exception as e2:
            print(f"❌ Migration with fake initial also failed: {e2}")
            return
    
    # Create superuser
    print("\n👤 Creating superuser...")
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            print("✅ Superuser created: admin/admin123")
        else:
            print("ℹ️  Superuser already exists")
    except Exception as e:
        print(f"⚠️  Superuser creation failed: {e}")
    
    print("\n" + "=" * 40)
    print("🎉 Quick fix completed!")
    print("\n💡 Try accessing your admin panel now:")
    print("   - URL: https://your-render-url.onrender.com/admin/")
    print("   - Username: admin")
    print("   - Password: admin123")

if __name__ == "__main__":
    main() 