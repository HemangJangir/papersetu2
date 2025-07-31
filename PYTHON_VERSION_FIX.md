# Python Version Fix for Render Deployment

This guide addresses the `psycopg2` compatibility issue with Python 3.13+ when deploying to Render.

## 🚨 Problem

When deploying to Render with Python 3.13+, you may encounter this error:

```
django.core.exceptions.ImproperlyConfigured: Error loading psycopg2 or psycopg module
```

This happens because `psycopg2` is not fully compatible with Python 3.13+.

## ✅ Solution

### 1. Update `runtime.txt`

Create or update `runtime.txt` in your project root:

```txt
python-3.11.9
```

### 2. Update `requirements.txt`

Ensure your `requirements.txt` contains:

```txt
psycopg2==2.9.9
```

Instead of `psycopg2-binary==2.9.9` for better compatibility.

### 3. Update `render.yaml`

Update your `render.yaml` to specify Python 3.11.9:

```yaml
services:
  - type: web
    name: papersetu
    env: python
    buildCommand: chmod +x build.sh && ./build.sh
    startCommand: gunicorn conference_mgmt.wsgi:application --config gunicorn.conf.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: DJANGO_SETTINGS_MODULE
        value: conference_mgmt.settings
      - key: DEBUG
        value: False
      - key: ALLOWED_HOSTS
        value: papersetu2.onrender.com,*.onrender.com
```

### 4. Enhanced Build Script

The `build.sh` script now includes psycopg2 verification:

```bash
#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting PaperSetu deployment build..."
echo "🐍 Using Python 3.11.9 for psycopg2 compatibility..."

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
    echo "🔧 Verifying psycopg2 installation..."
    python -c "import psycopg2; print('✅ psycopg2 imported successfully')" || {
        echo "❌ psycopg2 import failed, trying alternative installation..."
        pip install psycopg2-binary==2.9.9
    }
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
```

## 🧪 Testing the Fix

### 1. Local Testing

Run the Python version check script:

```bash
python check_python_version.py
```

This will verify:
- Python version compatibility
- psycopg2 installation status
- Django database configuration

### 2. Database Configuration Check

```bash
python check_database.py
```

### 3. Local Development Setup

For Windows:
```bash
python setup_local_windows.py
```

For Linux/Mac:
```bash
python setup_local.py
```

## 🔧 Manual Installation (if needed)

If you need to manually install psycopg2:

### For Local Development (Windows)

```bash
# Try psycopg2 first
pip install psycopg2==2.9.9

# If that fails, try psycopg2-binary
pip install psycopg2-binary==2.9.9
```

### For Production (Render)

The build script will handle this automatically, but you can also:

1. Ensure `runtime.txt` contains `python-3.11.9`
2. Ensure `requirements.txt` contains `psycopg2==2.9.9`
3. Deploy to Render

## 📋 Deployment Checklist

Before deploying to Render:

- [ ] `runtime.txt` contains `python-3.11.9`
- [ ] `requirements.txt` contains `psycopg2==2.9.9`
- [ ] `render.yaml` specifies `PYTHON_VERSION: 3.11.9`
- [ ] `DATABASE_URL` environment variable is set in Render
- [ ] Run `python check_python_version.py` locally to verify
- [ ] Run `python check_database.py` to verify database config

## 🚀 Render Deployment Steps

1. **Push your changes to GitHub:**
   ```bash
   git add .
   git commit -m "Fix Python 3.13 psycopg2 compatibility issue"
   git push origin main
   ```

2. **In Render Dashboard:**
   - Go to your service
   - Click "Manual Deploy"
   - Select "Clear build cache & deploy"

3. **Monitor the build logs:**
   - Look for "Using Python 3.11.9 for psycopg2 compatibility"
   - Verify "psycopg2 imported successfully"
   - Check for any error messages

4. **Verify deployment:**
   - Check if the application loads
   - Test database connectivity
   - Verify admin interface works

## 🛠️ Troubleshooting

### Common Issues

1. **Build still fails with psycopg2 error:**
   - Ensure `runtime.txt` is in the root directory
   - Check that `requirements.txt` has the correct psycopg2 version
   - Clear build cache in Render

2. **Python version not changing:**
   - Render may cache the Python version
   - Try "Clear build cache & deploy" in Render
   - Check build logs for Python version confirmation

3. **Local development issues:**
   - Python 3.13+ is fine for local development with SQLite
   - Only production deployment needs Python 3.11.9
   - Use `python setup_local_windows.py` for Windows setup

### Alternative Solutions

If you still have issues:

1. **Use psycopg2-binary instead:**
   ```txt
   psycopg2-binary==2.9.9
   ```

2. **Try a different Python version:**
   ```txt
   python-3.12.0
   ```

3. **Use psycopg3 (newer alternative):**
   ```txt
   psycopg[binary]==3.1.18
   ```

## 📞 Support

If you continue to have issues:

1. Check the Render build logs for specific error messages
2. Run `python check_python_version.py` locally
3. Verify all configuration files are correct
4. Check the [Render documentation](https://render.com/docs/python-versions)

---

**Note:** This fix ensures compatibility with Render's PostgreSQL service while maintaining local development flexibility. 