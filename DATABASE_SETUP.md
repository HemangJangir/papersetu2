# Database Setup Guide for PaperSetu

This guide explains how to set up the database for both local development and production deployment.

## 🏠 Local Development (SQLite)

For local development, the project automatically uses SQLite database.

### Quick Setup

1. **Run the setup script:**
   ```bash
   python setup_local.py
   ```

2. **Or manually:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Run migrations
   python manage.py migrate
   
   # Create superuser
   python manage.py createsuperuser
   
   # Collect static files
   python manage.py collectstatic --no-input
   ```

3. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

### Local Database Details
- **Database Engine:** SQLite
- **Database File:** `db.sqlite3` (in project root)
- **Admin Access:** http://127.0.0.1:8000/admin/
- **Default Credentials:** admin/admin123 (if created by setup script)

## 🚀 Production Deployment (PostgreSQL)

For production deployment on Render, the project automatically uses PostgreSQL.

### Environment Variables Required

Set these environment variables in your Render dashboard:

```bash
DATABASE_URL=postgresql://username:password@host:port/database_name
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,*.onrender.com
```

### Production Database Details
- **Database Engine:** PostgreSQL
- **Connection:** Via DATABASE_URL environment variable
- **SSL Mode:** Required
- **Connection Pooling:** Enabled (max_age=600)

## 🔧 Database Configuration

The database configuration is automatically handled in `conference_mgmt/settings.py`:

```python
# Check if we're in production (Render) or development
IS_PRODUCTION = os.environ.get('DATABASE_URL') is not None

if IS_PRODUCTION:
    # Use PostgreSQL in production
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Use SQLite in development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

## 🧪 Testing Database Configuration

Run the database check script to verify your configuration:

```bash
python check_database.py
```

This script will:
- Check if you're using the correct database
- Test database connectivity
- Verify migrations are applied
- Show basic statistics

## 📊 Database Management Commands

### View Database Status
```bash
python manage.py manage_production_db status
```

### List All Users
```bash
python manage.py list_all_users
```

### List All Conferences
```bash
python manage.py list_all_conferences
```

### Create Superuser
```bash
python manage.py manage_production_db create_superuser --username admin --email admin@example.com --password admin123
```

## 🔄 Migrations

### Apply Migrations
```bash
python manage.py migrate
```

### Show Migration Status
```bash
python manage.py showmigrations
```

### Create New Migration
```bash
python manage.py makemigrations
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check if DATABASE_URL is set correctly
   - Verify database credentials
   - Ensure database server is running

2. **Migration Errors**
   - Run `python manage.py migrate --fake-initial` if needed
   - Check for conflicting migrations

3. **Permission Errors**
   - Ensure database user has proper permissions
   - Check file permissions for SQLite

### Reset Database (Development Only)

```bash
# Remove SQLite database
rm db.sqlite3

# Recreate database
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## 📝 Environment Variables Reference

| Variable | Development | Production | Description |
|----------|-------------|------------|-------------|
| `DATABASE_URL` | Not set | Required | PostgreSQL connection string |
| `DEBUG` | True | False | Django debug mode |
| `SECRET_KEY` | Optional | Required | Django secret key |
| `ALLOWED_HOSTS` | localhost | your-domain.com | Allowed hosts |

## 🎯 Quick Start Checklist

### For Local Development:
- [ ] Run `python setup_local.py`
- [ ] Verify with `python check_database.py`
- [ ] Start server with `python manage.py runserver`
- [ ] Access admin at http://127.0.0.1:8000/admin/

### For Production:
- [ ] Set `DATABASE_URL` environment variable
- [ ] Set `DEBUG=False`
- [ ] Set `SECRET_KEY`
- [ ] Deploy to Render
- [ ] Verify deployment with `python check_database.py`

## 📞 Support

If you encounter any database-related issues:

1. Run `python check_database.py` to diagnose
2. Check the logs in the `logs/` directory
3. Verify environment variables are set correctly
4. Ensure all dependencies are installed

---

**Note:** The project automatically detects the environment and uses the appropriate database configuration. No manual configuration changes are needed! 