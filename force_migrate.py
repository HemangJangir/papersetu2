#!/usr/bin/env python3
"""
Force Migration Script for Render
This script forces the creation of missing tables and runs all migrations.
"""

import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.db import migrations
from django.apps import apps

def force_create_tables():
    """Force create missing tables"""
    print("🔧 Force creating missing tables...")
    
    try:
        # Get all models
        app_configs = apps.get_app_configs()
        
        for app_config in app_configs:
            if app_config.name in ['accounts', 'conference', 'dashboard']:
                print(f"📋 Processing app: {app_config.name}")
                
                # Get models for this app
                models = app_config.get_models()
                
                for model in models:
                    table_name = model._meta.db_table
                    print(f"  - Checking table: {table_name}")
                    
                    # Check if table exists
                    with connection.cursor() as cursor:
                        cursor.execute(f"""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = '{table_name}'
                            );
                        """)
                        result = cursor.fetchone()
                        
                        if not result or not result[0]:
                            print(f"    ❌ Table {table_name} missing - creating...")
                            # Create table using Django's create_model method
                            with connection.schema_editor() as schema_editor:
                                schema_editor.create_model(model)
                            print(f"    ✅ Table {table_name} created")
                        else:
                            print(f"    ✅ Table {table_name} exists")
    
    except Exception as e:
        print(f"⚠️  Force table creation failed: {e}")

def run_migrations_with_retry():
    """Run migrations with multiple retry strategies"""
    print("\n🔄 Running migrations with retry strategies...")
    
    strategies = [
        (['manage.py', 'migrate', '--no-input'], "Normal migration"),
        (['manage.py', 'migrate', '--fake-initial', '--no-input'], "Fake initial migration"),
        (['manage.py', 'migrate', '--run-syncdb', '--no-input'], "Sync database"),
        (['manage.py', 'migrate', '--fake', '--no-input'], "Fake all migrations"),
    ]
    
    for cmd, description in strategies:
        print(f"\n🔄 Trying: {description}")
        try:
            execute_from_command_line(cmd)
            print(f"✅ {description} successful")
            return True
        except Exception as e:
            print(f"❌ {description} failed: {e}")
            continue
    
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
    print("🚀 Force Migration Script for Render")
    print("=" * 50)
    
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
    
    # Force create missing tables
    force_create_tables()
    
    # Run migrations with retry
    if not run_migrations_with_retry():
        print("\n❌ All migration strategies failed")
        return
    
    # Create superuser
    create_superuser()
    
    print("\n" + "=" * 50)
    print("🎉 Force migration completed!")
    print("\n💡 Try accessing your admin panel now:")
    print("   - URL: https://your-render-url.onrender.com/admin/")
    print("   - Username: admin")
    print("   - Password: admin123")

if __name__ == "__main__":
    main() 