from django.shortcuts import render
from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
import os
import logging

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'homepage.html')

def custom_404(request, exception):
    """Custom 404 error handler"""
    logger.warning(f'404 error for URL: {request.path} from IP: {request.META.get("REMOTE_ADDR", "unknown")}')
    return render(request, '404.html', status=404)

def custom_500(request):
    """Custom 500 error handler"""
    logger.error(f'500 error for URL: {request.path} from IP: {request.META.get("REMOTE_ADDR", "unknown")}')
    return render(request, '500.html', status=500)

def custom_403(request, exception):
    """Custom 403 error handler"""
    logger.warning(f'403 error for URL: {request.path} from IP: {request.META.get("REMOTE_ADDR", "unknown")}')
    return render(request, '403.html', status=403)

def health_check(request):
    """Health check endpoint for monitoring"""
    return HttpResponse("OK", content_type="text/plain")

@csrf_exempt
def run_migrations(request):
    """Temporary view to run migrations - DELETE AFTER USE"""
    if request.method == 'POST':
        try:
            # Run migrations
            call_command('migrate', '--no-input')
            
            # Check if accounts_user table exists
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'accounts_user'
                    );
                """)
                result = cursor.fetchone()
                
                if result and result[0]:
                    return HttpResponse("""
                        <h2>✅ Migrations Completed Successfully!</h2>
                        <p>The accounts_user table now exists.</p>
                        <p><a href="/create-superuser/">Click here to create superuser</a></p>
                        <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
                    """)
                else:
                    return HttpResponse("""
                        <h2>❌ Migration Failed</h2>
                        <p>The accounts_user table still doesn't exist.</p>
                        <p>Check the logs for more details.</p>
                    """)
        except Exception as e:
            return HttpResponse(f"""
                <h2>❌ Migration Error</h2>
                <p>Error: {str(e)}</p>
                <p>Check the logs for more details.</p>
            """)
    
    return HttpResponse("""
        <h2>🚀 Run Migrations</h2>
        <p>This will run all Django migrations to create the missing tables.</p>
        <form method="post">
            <button type="submit" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                Run Migrations
            </button>
        </form>
        <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
    """)

@csrf_exempt
def create_superuser(request):
    """Temporary view to create superuser - DELETE AFTER USE"""
    if request.method == 'POST':
        try:
            User = get_user_model()
            
            # Check if admin user already exists
            if User.objects.filter(username='admin').exists():
                return HttpResponse("""
                    <h2>ℹ️ Superuser Already Exists</h2>
                    <p>The admin user already exists.</p>
                    <p><a href="/admin/">Go to Admin Panel</a></p>
                    <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
                """)
            
            # Create superuser
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            
            return HttpResponse("""
                <h2>✅ Superuser Created Successfully!</h2>
                <p><strong>Username:</strong> admin</p>
                <p><strong>Password:</strong> admin123</p>
                <p><a href="/admin/">Go to Admin Panel</a></p>
                <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
            """)
        except Exception as e:
            return HttpResponse(f"""
                <h2>❌ Superuser Creation Error</h2>
                <p>Error: {str(e)}</p>
                <p>Check the logs for more details.</p>
            """)
    
    return HttpResponse("""
        <h2>👤 Create Superuser</h2>
        <p>This will create a superuser account for admin access.</p>
        <form method="post">
            <button type="submit" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                Create Superuser
            </button>
        </form>
        <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
    """)

@csrf_exempt
def check_database(request):
    """Temporary view to check database status - DELETE AFTER USE"""
    try:
        from django.db import connection
        
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            db_connected = result and result[0] == 1
            
            # Check if accounts_user table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'accounts_user'
                );
            """)
            result = cursor.fetchone()
            table_exists = result and result[0]
            
            # Check if admin user exists
            User = get_user_model()
            admin_exists = User.objects.filter(username='admin').exists()
            
            return HttpResponse(f"""
                <h2>🔍 Database Status Check</h2>
                <p><strong>Database Connected:</strong> {'✅ Yes' if db_connected else '❌ No'}</p>
                <p><strong>accounts_user Table:</strong> {'✅ Exists' if table_exists else '❌ Missing'}</p>
                <p><strong>Admin User:</strong> {'✅ Exists' if admin_exists else '❌ Missing'}</p>
                <br>
                <p><a href="/run-migrations/">Run Migrations</a> | <a href="/create-superuser/">Create Superuser</a></p>
                <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
            """)
    except Exception as e:
        return HttpResponse(f"""
            <h2>❌ Database Check Error</h2>
            <p>Error: {str(e)}</p>
        """) 