#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting PaperSetu deployment build..."
echo "🐍 Using Python 3.13+ with psycopg3 compatibility..."

# Check Python version
echo "📋 Python version check..."
python --version

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p staticfiles
mkdir -p media

# Check database configuration
echo "🔍 Checking database configuration..."
if [ -n "$DATABASE_URL" ]; then
    echo "✅ Using PostgreSQL (Production)"
    echo "🔧 Verifying psycopg3 installation..."
    python -c "import psycopg; print('✅ psycopg3 imported successfully')" || {
        echo "❌ psycopg3 import failed, trying alternative installation..."
        pip install psycopg[binary]==3.2.9
    }
    
    # Test database connection
    echo "🔍 Testing database connection..."
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT 1')
    print('✅ Database connection successful')
" || {
        echo "❌ Database connection failed"
        exit 1
    }
else
    echo "⚠️  No DATABASE_URL found - using SQLite (Development)"
fi

# Collect static files including admin
echo "📦 Collecting static files..."
python manage.py collectstatic --no-input --clear

# Show migration status before running
echo "📋 Checking migration status..."
python manage.py showmigrations --list || echo "⚠️  Could not show migrations"

# Run migrations with better error handling
echo "🔄 Running database migrations..."
python manage.py migrate --no-input --verbosity=2 || {
    echo "❌ Migration failed, trying with fake initial..."
    python manage.py migrate --fake-initial --no-input --verbosity=2 || {
        echo "❌ Migration failed completely"
        exit 1
    }
}

# Verify migrations were applied
echo "✅ Verifying migrations..."
python manage.py showmigrations --list || echo "⚠️  Could not verify migrations"

# Setup admin interface (if command exists)
echo "⚙️  Setting up admin interface..."
python manage.py setup_admin_interface || echo "Admin interface setup skipped"

# Create superuser if it doesn't exist (optional)
echo "👤 Creating superuser..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️  Superuser already exists')
" || echo "⚠️  Superuser creation failed"

echo "✅ Build completed successfully!" 