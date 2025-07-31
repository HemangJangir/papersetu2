#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting PaperSetu deployment build..."

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
else
    echo "⚠️  No DATABASE_URL found - using SQLite (Development)"
fi

# Collect static files including admin
echo "📦 Collecting static files..."
python manage.py collectstatic --no-input --clear

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate --no-input

# Setup admin interface (if command exists)
echo "⚙️  Setting up admin interface..."
python manage.py setup_admin_interface || echo "Admin interface setup skipped"

# Create superuser if it doesn't exist (optional)
echo "👤 Creating superuser..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell || echo "Superuser creation skipped"

echo "✅ Build completed successfully!" 