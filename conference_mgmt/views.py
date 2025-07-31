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
            
            # Get ALL tables in the database
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            all_tables = [row[0] for row in cursor.fetchall()]
            
            # Check specific important tables
            important_tables = [
                'accounts_user',
                'accounts_emailverification',
                'conference_conference',
                'conference_paper',
                'conference_review',
                'conference_userconferencerole',
                'conference_track',
                'conference_subreviewerinvite',
                'conference_pcinvite',
                'conference_registrationapplication',
                'django_migrations',
                'django_content_type',
                'django_admin_log',
                'django_session',
                'django_site'
            ]
            
            table_status = {}
            for table in important_tables:
                table_status[table] = table in all_tables
            
            # Check if admin user exists
            User = get_user_model()
            admin_exists = User.objects.filter(username='admin').exists()
            
            # Create detailed status report
            status_html = f"""
                <h2>🔍 Complete Database Status Check</h2>
                <p><strong>Database Connected:</strong> {'✅ Yes' if db_connected else '❌ No'}</p>
                <p><strong>Total Tables Found:</strong> {len(all_tables)}</p>
                <p><strong>Admin User:</strong> {'✅ Exists' if admin_exists else '❌ Missing'}</p>
                
                <h3>📋 Important Tables Status:</h3>
                <table border="1" style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 8px;">Table Name</th>
                        <th style="padding: 8px;">Status</th>
                    </tr>
            """
            
            for table in important_tables:
                status = "✅ Exists" if table_status[table] else "❌ Missing"
                color = "green" if table_status[table] else "red"
                status_html += f"""
                    <tr>
                        <td style="padding: 8px;">{table}</td>
                        <td style="padding: 8px; color: {color};">{status}</td>
                    </tr>
                """
            
            status_html += """
                </table>
                
                <h3>🗄️ All Tables in Database:</h3>
                <div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto;">
            """
            
            if all_tables:
                for table in all_tables:
                    status_html += f"<div>• {table}</div>"
            else:
                status_html += "<div>No tables found!</div>"
            
            status_html += """
                </div>
                
                <br>
                <p><a href="/run-migrations/">🔄 Run Migrations</a> | <a href="/create-superuser/">👤 Create Superuser</a></p>
                <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
            """
            
            return HttpResponse(status_html)
            
    except Exception as e:
        return HttpResponse(f"""
            <h2>❌ Database Check Error</h2>
            <p>Error: {str(e)}</p>
            <p><a href="/run-migrations/">🔄 Run Migrations</a></p>
        """)

@csrf_exempt
def complete_migration(request):
    """Temporary view to run complete migration - DELETE AFTER USE"""
    if request.method == 'POST':
        try:
            # Run the complete migration script
            import subprocess
            result = subprocess.run(['python', 'complete_migration.py'], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return HttpResponse(f"""
                    <h2>✅ Complete Migration Successful!</h2>
                    <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px; max-height: 400px; overflow-y: auto;">{result.stdout}</pre>
                    <p><a href="/check-database/">Check Database Status</a></p>
                    <p><a href="/create-superuser/">Create Superuser</a></p>
                    <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
                """)
            else:
                return HttpResponse(f"""
                    <h2>❌ Complete Migration Failed</h2>
                    <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px; max-height: 400px; overflow-y: auto;">{result.stderr}</pre>
                    <p><a href="/run-migrations/">Try Simple Migration</a></p>
                    <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
                """)
        except Exception as e:
            return HttpResponse(f"""
                <h2>❌ Complete Migration Error</h2>
                <p>Error: {str(e)}</p>
                <p><a href="/run-migrations/">Try Simple Migration</a></p>
                <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
            """)
    
    return HttpResponse("""
        <h2>🚀 Complete Migration</h2>
        <p>This will run a comprehensive migration to ensure ALL tables from your local server are created in PostgreSQL.</p>
        <p><strong>This includes:</strong></p>
        <ul>
            <li>All accounts tables (user, email verification)</li>
            <li>All conference tables (conference, paper, review, etc.)</li>
            <li>All dashboard tables</li>
            <li>All Django core tables</li>
        </ul>
        <form method="post">
            <button type="submit" style="background: #dc3545; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                Run Complete Migration
            </button>
        </form>
        <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
    """) 

@csrf_exempt
def fix_missing_tables(request):
    """Temporary view to fix missing tables - DELETE AFTER USE"""
    if request.method == 'POST':
        try:
            # Run the fix missing tables script
            import subprocess
            result = subprocess.run(['python', 'fix_missing_tables.py'], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return HttpResponse(f"""
                    <h2>✅ Missing Tables Fixed Successfully!</h2>
                    <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px; max-height: 400px; overflow-y: auto;">{result.stdout}</pre>
                    <p><a href="/check-database/">Check Database Status</a></p>
                    <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
                """)
            else:
                return HttpResponse(f"""
                    <h2>❌ Fix Missing Tables Failed</h2>
                    <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px; max-height: 400px; overflow-y: auto;">{result.stderr}</pre>
                    <p><a href="/complete-migration/">Try Complete Migration</a></p>
                    <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
                """)
        except Exception as e:
            return HttpResponse(f"""
                <h2>❌ Fix Missing Tables Error</h2>
                <p>Error: {str(e)}</p>
                <p><a href="/complete-migration/">Try Complete Migration</a></p>
                <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
            """)
    
    return HttpResponse("""
        <h2>🔧 Fix Missing Tables</h2>
        <p>This will specifically create the missing tables:</p>
        <ul>
            <li>accounts_emailverification</li>
            <li>django_site</li>
        </ul>
        <form method="post">
            <button type="submit" style="background: #ffc107; color: black; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                Fix Missing Tables
            </button>
        </form>
        <p><strong>⚠️ IMPORTANT: Delete this view after use!</strong></p>
    """) 