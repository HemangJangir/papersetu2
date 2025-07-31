#!/usr/bin/env python3
"""
Local Development Setup Script for PaperSetu (Windows)
This script helps set up the project for local development with SQLite on Windows.
"""

import os
import sys
import subprocess
import django
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    current_version = sys.version_info
    print(f"🐍 Python version: {current_version.major}.{current_version.minor}.{current_version.micro}")
    
    if current_version.major == 3 and current_version.minor >= 13:
        print("✅ Python 3.13+ detected - Compatible with psycopg3!")
        return True
    elif current_version.major == 3 and current_version.minor == 11:
        print("✅ Python 3.11 detected - Compatible with psycopg3!")
        return True
    else:
        print("✅ Python version should work fine for local development")
        return True

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

def install_packages_windows():
    """Install packages one by one to avoid PostgreSQL build issues"""
    print("📦 Installing packages for Windows...")
    
    # Core packages (no PostgreSQL dependency)
    core_packages = [
        "Django==5.2.3",
        "django-admin-interface==0.30.1", 
        "django-colorfield==0.14.0",
        "django-widget-tweaks==1.5.0",
        "dj-database-url==3.0.1",
        "bcrypt==4.1.2",
        "cryptography==41.0.7",
        "requests==2.32.4",
        "Pillow==11.3.0",
        "openpyxl==3.1.5",
        "python-dateutil==2.9.0.post0",
        "python-dotenv==1.1.1",
        "pytz==2025.2",
        "PyYAML==6.0.2",
        "social-auth-app-django==5.4.3",
        "social-auth-core==4.6.1",
        "stripe==5.0.0",
        "asgiref==3.8.1",
        "sqlparse==0.5.3"
    ]
    
    for package in core_packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            print(f"⚠️  Failed to install {package}, but continuing...")
    
    # Try to install psycopg3 (optional for local development)
    print("\n🔄 Trying to install PostgreSQL adapter (optional for local development)...")
    try:
        # Try psycopg3
        subprocess.run("pip install psycopg[binary]==3.2.9", shell=True, check=True, capture_output=True, text=True)
        print("✅ psycopg3 installed successfully")
    except subprocess.CalledProcessError:
        print("⚠️  PostgreSQL adapter installation failed (this is OK for local development with SQLite)")
        print("💡 You can install it later if needed for production deployment")
    
    return True

def setup_local_environment():
    """Set up local development environment"""
    print("🚀 Setting up PaperSetu for local development on Windows...")
    
    # Check Python version
    check_python_version()
    
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
    
    # Install dependencies (Windows-friendly approach)
    if not install_packages_windows():
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
    print("\n⚠️  Note: PostgreSQL adapter installation was attempted for local development.")
    print("   For production deployment, psycopg3 is now compatible with Python 3.13+!")
    
    return True

if __name__ == "__main__":
    success = setup_local_environment()
    if success:
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1) 