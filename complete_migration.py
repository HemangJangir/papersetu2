#!/usr/bin/env python3
"""
Complete Migration Script for Render
This script ensures ALL tables from local server are created in PostgreSQL.
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

def get_all_models():
    """Get all models from all apps"""
    all_models = []
    for app_config in apps.get_app_configs():
        if app_config.name in ['accounts', 'conference', 'dashboard']:
            models = app_config.get_models()
            all_models.extend(models)
    return all_models

def check_all_tables():
    """Check all tables that should exist"""
    print("🔍 Checking all required tables...")
    
    # Get all models
    all_models = get_all_models()
    
    # Get existing tables
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
    
    print(f"Found {len(existing_tables)} existing tables")
    print(f"Expected {len(all_models)} model tables")
    
    # Check each model's table
    missing_tables = []
    for model in all_models:
        table_name = model._meta.db_table
        if table_name not in existing_tables:
            missing_tables.append(table_name)
            print(f"❌ Missing: {table_name}")
        else:
            print(f"✅ Exists: {table_name}")
    
    return missing_tables, existing_tables

def run_complete_migration():
    """Run complete migration with all strategies"""
    print("🔄 Running complete migration...")
    
    strategies = [
        (['manage.py', 'migrate', '--no-input', '--verbosity=2'], "Normal migration"),
        (['manage.py', 'migrate', '--fake-initial', '--no-input', '--verbosity=2'], "Fake initial migration"),
        (['manage.py', 'migrate', '--run-syncdb', '--no-input', '--verbosity=2'], "Sync database"),
        (['manage.py', 'migrate', '--fake', '--no-input', '--verbosity=2'], "Fake all migrations"),
    ]
    
    for cmd, description in strategies:
        print(f"\n🔄 Trying: {description}")
        try:
            execute_from_command_line(cmd)
            print(f"✅ {description} successful")
            
            # Check if all tables exist now
            missing_tables, existing_tables = check_all_tables()
            if not missing_tables:
                print("🎉 All tables created successfully!")
                return True
            else:
                print(f"⚠️  Still missing {len(missing_tables)} tables")
                
        except Exception as e:
            print(f"❌ {description} failed: {e}")
            continue
    
    return False

def force_create_missing_tables(missing_tables):
    """Force create missing tables"""
    print(f"\n🔧 Force creating {len(missing_tables)} missing tables...")
    
    try:
        all_models = get_all_models()
        model_dict = {model._meta.db_table: model for model in all_models}
        
        with connection.schema_editor() as schema_editor:
            for table_name in missing_tables:
                if table_name in model_dict:
                    model = model_dict[table_name]
                    print(f"  Creating table: {table_name}")
                    schema_editor.create_model(model)
                    print(f"  ✅ Created: {table_name}")
                else:
                    print(f"  ⚠️  Model not found for table: {table_name}")
        
        return True
    except Exception as e:
        print(f"❌ Force table creation failed: {e}")
        return False

def create_superuser():
    """Create superuser"""
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

def main():
    print("🚀 Complete Migration Script for Render")
    print("=" * 60)
    
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
    
    # Check current table status
    print("\n📋 Current table status:")
    missing_tables, existing_tables = check_all_tables()
    
    if not missing_tables:
        print("\n🎉 All tables already exist!")
    else:
        print(f"\n🔄 {len(missing_tables)} tables missing, running migrations...")
        
        # Try normal migration first
        if run_complete_migration():
            print("\n✅ Migration completed successfully!")
        else:
            print("\n⚠️  Normal migration failed, trying force creation...")
            
            # Force create missing tables
            if force_create_missing_tables(missing_tables):
                print("\n✅ Force table creation completed!")
            else:
                print("\n❌ Force table creation failed")
                return
    
    # Create superuser
    create_superuser()
    
    # Final check
    print("\n📋 Final table status:")
    missing_tables, existing_tables = check_all_tables()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total tables in database: {len(existing_tables)}")
    print(f"Missing tables: {len(missing_tables)}")
    
    if not missing_tables:
        print("🎉 SUCCESS: All tables created!")
        print("\n💡 You can now:")
        print("  - Register new users")
        print("  - Create conferences")
        print("  - Submit papers")
        print("  - Use the full application")
    else:
        print("❌ Some tables are still missing")
        print("Check the logs for more details")

if __name__ == "__main__":
    main() 