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

# Run migrations with multiple strategies
echo "🔄 Running migrations with multiple strategies..."

# Strategy 1: Normal migration
echo "🔄 Strategy 1: Normal migration..."
python manage.py migrate --no-input --verbosity=2 || {
    echo "❌ Normal migration failed, trying Strategy 2..."
    
    # Strategy 2: Fake initial migration
    echo "🔄 Strategy 2: Fake initial migration..."
    python manage.py migrate --fake-initial --no-input --verbosity=2 || {
        echo "❌ Fake initial migration failed, trying Strategy 3..."
        
        # Strategy 3: Sync database
        echo "🔄 Strategy 3: Sync database..."
        python manage.py migrate --run-syncdb --no-input --verbosity=2 || {
            echo "❌ Sync database failed, trying Strategy 4..."
            
            # Strategy 4: Force migration script
            echo "🔄 Strategy 4: Force migration script..."
            python force_migrate.py || {
                echo "❌ Force migration failed, trying Strategy 5..."
                
                # Strategy 5: Quick fix script
                echo "🔄 Strategy 5: Quick fix script..."
                python quick_fix_migrations.py || {
                    echo "❌ All migration strategies failed"
                    exit 1
                }
            }
        }
    }
}

# Verify migrations were applied
echo "✅ Verifying migrations..."
python manage.py showmigrations --list || echo "⚠️  Could not verify migrations"

# Check if accounts_user table exists
echo "🔍 Checking if accounts_user table exists..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"\"\"
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'accounts_user'
        );
    \"\"\")
    result = cursor.fetchone()
    if result and result[0]:
        print('✅ accounts_user table exists')
    else:
        print('❌ accounts_user table does not exist - running quick fix...')
        import subprocess
        subprocess.run(['python', 'quick_fix_migrations.py'], check=True)
" || {
    echo "❌ Table check failed, running quick fix..."
    python quick_fix_migrations.py || python force_migrate.py
}

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