#!/usr/bin/env python3
"""
Local Development Setup Script for PaperSetu
This script helps set up the project for local development with SQLite.
"""

import os
import sys
import subprocess
import django
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def setup_local_environment():
    """Set up local development environment"""
    print("🚀 Setting up PaperSetu for local development...")
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the project root directory.")
        return False
    
    # Set environment variables for local development
    os.environ.setdefault('DEBUG', 'True')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
    
    # Remove DATABASE_URL to force SQLite usage
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
        print("ℹ️  Removed DATABASE_URL to use SQLite for local development")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False
    
    # Create necessary directories
    directories = ['logs', 'media', 'staticfiles']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Run migrations
    if not run_command("python manage.py migrate", "Running database migrations"):
        return False
    
    # Collect static files
    if not run_command("python manage.py collectstatic --no-input", "Collecting static files"):
        return False
    
    # Create superuser
    print("\n👤 Creating superuser for local development...")
    superuser_script = """
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"""
    
    try:
        subprocess.run([sys.executable, 'manage.py', 'shell'], 
                      input=superuser_script, text=True, check=True)
        print("✅ Superuser setup completed")
    except subprocess.CalledProcessError:
        print("⚠️  Superuser creation failed, but you can create one manually later")
    
    print("\n🎉 Local development setup completed!")
    print("\n📋 Next steps:")
    print("1. Run the development server: python manage.py runserver")
    print("2. Open http://127.0.0.1:8000 in your browser")
    print("3. Login with admin/admin123")
    print("\n💡 Database: SQLite (db.sqlite3)")
    print("💡 Debug mode: Enabled")
    
    return True

if __name__ == "__main__":
    success = setup_local_environment()
    if success:
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1) 