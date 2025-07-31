#!/usr/bin/env python3
"""
Migration Fix Script for Render Deployment
This script helps fix migration issues on Render.
"""

import os
import sys
import django
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.conf import settings

def check_database_connection():
    """Check if database connection is working"""
    print("🔍 Checking database connection...")
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

def check_migration_status():
    """Check current migration status"""
    print("\n📋 Checking migration status...")
    try:
        # Run showmigrations command
        execute_from_command_line(['manage.py', 'showmigrations', '--list'])
        return True
    except Exception as e:
        print(f"❌ Could not check migration status: {e}")
        return False

def run_migrations():
    """Run migrations with error handling"""
    print("\n🔄 Running migrations...")
    try:
        # First try normal migration
        execute_from_command_line(['manage.py', 'migrate', '--no-input', '--verbosity=2'])
        print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"⚠️  Normal migration failed: {e}")
        print("🔄 Trying with fake initial...")
        try:
            execute_from_command_line(['manage.py', 'migrate', '--fake-initial', '--no-input', '--verbosity=2'])
            print("✅ Migrations completed with fake initial")
            return True
        except Exception as e2:
            print(f"❌ Migration with fake initial also failed: {e2}")
            return False

def create_superuser():
    """Create superuser if it doesn't exist"""
    print("\n👤 Creating superuser...")
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            print("✅ Superuser created: admin/admin123")
        else:
            print("ℹ️  Superuser already exists")
        return True
    except Exception as e:
        print(f"❌ Superuser creation failed: {e}")
        return False

def check_tables():
    """Check if required tables exist"""
    print("\n🔍 Checking if required tables exist...")
    try:
        with connection.cursor() as cursor:
            # Check for accounts_user table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'accounts_user'
                );
            """)
            result = cursor.fetchone()
            if result and result[0]:
                print("✅ accounts_user table exists")
            else:
                print("❌ accounts_user table does not exist")
                return False
            
            # Check for other important tables
            tables_to_check = [
                'django_migrations',
                'django_content_type',
                'django_admin_log',
                'conference_conference'
            ]
            
            for table in tables_to_check:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    );
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    print(f"✅ {table} table exists")
                else:
                    print(f"❌ {table} table does not exist")
            
            return True
    except Exception as e:
        print(f"❌ Could not check tables: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Migration Fix Script for Render")
    print("=" * 50)
    
    # Check if we're in production
    is_production = os.environ.get('DATABASE_URL') is not None
    print(f"Environment: {'Production (PostgreSQL)' if is_production else 'Development (SQLite)'}")
    
    # Check database connection
    if not check_database_connection():
        print("\n❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Check migration status
    check_migration_status()
    
    # Run migrations
    if not run_migrations():
        print("\n❌ Migration failed")
        sys.exit(1)
    
    # Check tables after migration
    if not check_tables():
        print("\n❌ Required tables are missing")
        sys.exit(1)
    
    # Create superuser
    create_superuser()
    
    print("\n" + "=" * 50)
    print("🎉 Migration fix completed!")
    print("\n💡 Next steps:")
    print("1. Try accessing your admin panel again")
    print("2. Login with admin/admin123")
    print("3. If issues persist, check Render logs")

if __name__ == "__main__":
    main() 