#!/usr/bin/env python3
"""
Fix Missing Tables Script
This script specifically creates the missing accounts_emailverification and django_site tables.
"""

import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def create_missing_tables():
    """Create the specific missing tables"""
    print("🔧 Creating missing tables...")
    
    # Check if accounts_emailverification table exists
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'accounts_emailverification'
            );
        """)
        email_verification_exists = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'django_site'
            );
        """)
        django_site_exists = cursor.fetchone()[0]
    
    print(f"accounts_emailverification exists: {email_verification_exists}")
    print(f"django_site exists: {django_site_exists}")
    
    # Create accounts_emailverification table if missing
    if not email_verification_exists:
        print("Creating accounts_emailverification table...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE accounts_emailverification (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        token VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        is_verified BOOLEAN NOT NULL DEFAULT FALSE
                    );
                """)
                print("✅ accounts_emailverification table created")
        except Exception as e:
            print(f"❌ Error creating accounts_emailverification: {e}")
    
    # Skip django_site table since sites app is not installed
    if not django_site_exists:
        print("⚠️  Skipping django_site table creation - django.contrib.sites not in INSTALLED_APPS")
    
    # Run specific migrations for these apps
    print("\n🔄 Running specific migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate', 'accounts', '--no-input'])
        print("✅ accounts migrations completed")
    except Exception as e:
        print(f"⚠️  accounts migration failed: {e}")
    
    # Skip sites migration since sites app is not installed
    print("⚠️  Skipping sites migration - django.contrib.sites not in INSTALLED_APPS")

def check_tables_after_fix():
    """Check if tables exist after fix"""
    print("\n🔍 Checking tables after fix...")
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'accounts_emailverification'
            );
        """)
        email_verification_exists = cursor.fetchone()[0]
    
    print(f"accounts_emailverification: {'✅ Exists' if email_verification_exists else '❌ Missing'}")
    print("django_site: ⚠️  Skipped (not needed - sites app not installed)")
    
    return email_verification_exists

def main():
    print("🚀 Fix Missing Tables Script")
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
    
    # Create missing tables
    create_missing_tables()
    
    # Check if fix worked
    success = check_tables_after_fix()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: All missing tables created!")
    else:
        print("❌ Some tables are still missing")
        print("Check the logs for more details")

if __name__ == "__main__":
    main() 