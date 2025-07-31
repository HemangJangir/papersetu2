# Migration Fix Guide for Render Deployment

This guide helps fix the "relation 'accounts_user' does not exist" error on Render.

## 🚨 Problem

When accessing the admin panel on your Render deployment, you get this error:

```
ProgrammingError at /admin/login/
relation "accounts_user" does not exist
LINE 1: ...ser"."otp", "accounts_user"."otp_created_at" FROM "accounts_...
```

This happens because the database migrations haven't been applied properly.

## ✅ Solution Steps

### Step 1: Deploy the Updated Build Script

First, commit and push the updated `build.sh` file:

```bash
git add .
git commit -m "Fix migration issues with enhanced build script"
git push origin main
```

### Step 2: Redeploy on Render

1. Go to your Render dashboard
2. Click "Manual Deploy"
3. Select "Clear build cache & deploy"
4. Monitor the build logs

### Step 3: Check Build Logs

Look for these success indicators in the build logs:

```
🚀 Starting PaperSetu deployment build...
🐍 Using Python 3.13+ with psycopg3 compatibility...
📋 Python version check...
Python 3.13.x
📦 Installing dependencies...
🔧 Verifying psycopg3 installation...
✅ psycopg3 imported successfully
🔍 Testing database connection...
✅ Database connection successful
📦 Collecting static files...
📋 Checking migration status...
🔄 Running database migrations...
✅ Migrations completed successfully
✅ Verifying migrations...
👤 Creating superuser...
✅ Superuser created: admin/admin123
✅ Build completed successfully!
```

### Step 4: Manual Migration Fix (if needed)

If the build still doesn't fix the issue, you can run the migration fix manually.

#### Option A: Using the Management Command

1. **Access Render Shell:**
   - Go to your Render service
   - Click "Shell" tab
   - Run the migration fix command:

```bash
python manage.py fix_render_migrations --force
```

#### Option B: Using the Python Script

1. **Upload the fix script:**
   - Add `fix_migrations.py` to your project
   - Deploy to Render

2. **Run the script:**
   ```bash
   python fix_migrations.py
   ```

### Step 5: Verify the Fix

After running the migration fix, verify that:

1. **Admin panel loads:** Try accessing `/admin/` again
2. **Login works:** Use admin/admin123
3. **Tables exist:** Check that required tables are created

## 🔧 Alternative Solutions

### If Migrations Still Fail

1. **Reset the database (if possible):**
   ```bash
   python manage.py flush --no-input
   python manage.py migrate --run-syncdb
   ```

2. **Use fake migrations:**
   ```bash
   python manage.py migrate --fake-initial
   ```

3. **Check migration conflicts:**
   ```bash
   python manage.py showmigrations --list
   ```

### If Database Connection Fails

1. **Check DATABASE_URL:**
   - Verify the environment variable is set correctly
   - Ensure the database is accessible

2. **Test connection manually:**
   ```bash
   python manage.py dbshell
   ```

3. **Check PostgreSQL logs:**
   - Look for connection errors
   - Verify database permissions

## 📋 Troubleshooting Checklist

### Before Deployment
- [ ] `DATABASE_URL` is set in Render environment variables
- [ ] PostgreSQL database is created and accessible
- [ ] All migration files are committed to git

### During Deployment
- [ ] Build script runs without errors
- [ ] psycopg3 installs successfully
- [ ] Database connection test passes
- [ ] Migrations run successfully
- [ ] Superuser is created

### After Deployment
- [ ] Admin panel loads without errors
- [ ] Login works with admin/admin123
- [ ] All required tables exist
- [ ] Application functions normally

## 🛠️ Common Issues and Solutions

### Issue: "No module named 'psycopg'"
**Solution:** The build script should handle this automatically, but if it fails:
```bash
pip install psycopg[binary]==3.2.9
```

### Issue: "Database connection failed"
**Solution:** Check your DATABASE_URL format:
```
postgresql://username:password@host:port/database_name
```

### Issue: "Permission denied"
**Solution:** Ensure your database user has proper permissions:
```sql
GRANT ALL PRIVILEGES ON DATABASE your_database TO your_user;
```

### Issue: "Migration conflicts"
**Solution:** Use fake migrations:
```bash
python manage.py migrate --fake-initial
```

## 📞 Getting Help

If you're still having issues:

1. **Check Render logs** for specific error messages
2. **Run the migration fix script** manually
3. **Verify environment variables** are set correctly
4. **Test database connection** manually
5. **Check PostgreSQL logs** for connection issues

## 🎯 Success Indicators

You'll know the fix worked when:

- ✅ Admin panel loads without errors
- ✅ Login works with admin/admin123
- ✅ All tables exist in the database
- ✅ Application functions normally
- ✅ No migration errors in logs

---

**Note:** The enhanced build script should automatically fix most migration issues. If problems persist, use the manual migration fix commands. 