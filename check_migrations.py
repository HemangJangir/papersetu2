#!/usr/bin/env python3
"""
Migration Status Check Script
This script checks the current migration status and helps debug issues.
"""

import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.apps import apps

def check_installed_apps():
    """Check if accounts app is properly installed"""
    print("🔍 Checking installed apps...")
    installed_apps = [app.name for app in apps.get_app_configs()]
    print(f"Installed apps: {installed_apps}")
    
    if 'accounts' in installed_apps:
        print("✅ accounts app is installed")
        return True
    else:
        print("❌ accounts app is NOT installed")
        return False

def check_migration_files():
    """Check if migration files exist"""
    print("\n📋 Checking migration files...")
    try:
        accounts_app = apps.get_app_config('accounts')
        migrations_dir = os.path.join(accounts_app.path, 'migrations')
        
        if os.path.exists(migrations_dir):
            migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.py') and f != '__init__.py']
            print(f"Migration files found: {migration_files}")
            return len(migration_files) > 0
        else:
            print("❌ migrations directory does not exist")
            return False
    except Exception as e:
        print(f"❌ Error checking migration files: {e}")
        return False

def check_database_tables():
    """Check what tables exist in the database"""
    print("\n🗄️  Checking database tables...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Tables in database: {tables}")
            
            if 'accounts_user' in tables:
                print("✅ accounts_user table exists")
                return True
            else:
                print("❌ accounts_user table does NOT exist")
                return False
    except Exception as e:
        print(f"❌ Error checking database tables: {e}")
        return False

def run_migrations():
    """Run migrations and show detailed output"""
    print("\n🔄 Running migrations...")
    try:
        # Show current migration status
        print("Current migration status:")
        execute_from_command_line(['manage.py', 'showmigrations', '--list'])
        
        # Run migrations
        print("\nRunning migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--no-input', '--verbosity=2'])
        
        print("✅ Migrations completed")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    print("🚀 Migration Status Check")
    print("=" * 50)
    
    # Check if we're in production
    is_production = os.environ.get('DATABASE_URL') is not None
    print(f"Environment: {'Production (PostgreSQL)' if is_production else 'Development (SQLite)'}")
    
    # Check database connection
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
    
    # Check installed apps
    if not check_installed_apps():
        print("\n❌ accounts app is not properly installed")
        return
    
    # Check migration files
    if not check_migration_files():
        print("\n❌ No migration files found")
        return
    
    # Check database tables
    table_exists = check_database_tables()
    
    # Run migrations if table doesn't exist
    if not table_exists:
        print("\n🔄 accounts_user table missing, running migrations...")
        if run_migrations():
            # Check again after migration
            if check_database_tables():
                print("\n🎉 SUCCESS: accounts_user table created!")
            else:
                print("\n❌ FAILED: accounts_user table still missing after migration")
        else:
            print("\n❌ FAILED: Migration could not be completed")
    else:
        print("\n✅ accounts_user table already exists")
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print("If the accounts_user table is missing, try these steps:")
    print("1. Visit: https://your-render-url.onrender.com/check-database/")
    print("2. Visit: https://your-render-url.onrender.com/run-migrations/")
    print("3. Visit: https://your-render-url.onrender.com/create-superuser/")

if __name__ == "__main__":
    main() 