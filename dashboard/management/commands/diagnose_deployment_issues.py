from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.cache import cache
import os
import sys
import requests
from urllib.parse import urlparse

User = get_user_model()

class Command(BaseCommand):
    help = 'Diagnose common deployment issues and errors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-url',
            type=str,
            help='Check specific URL for issues'
        )
        parser.add_argument(
            '--fix-common',
            action='store_true',
            help='Fix common deployment issues automatically'
        )

    def handle(self, *args, **options):
        if options.get('check_url'):
            self.check_specific_url(options['check_url'])
        elif options.get('fix_common'):
            self.fix_common_issues()
        else:
            self.diagnose_all_issues()

    def diagnose_all_issues(self):
        """Diagnose all common deployment issues"""
        self.stdout.write(self.style.SUCCESS('=== Deployment Issues Diagnosis ==='))
        
        # 1. Environment Configuration
        self.check_environment_config()
        
        # 2. Database Issues
        self.check_database_issues()
        
        # 3. Static Files Issues
        self.check_static_files_issues()
        
        # 4. Authentication Issues
        self.check_authentication_issues()
        
        # 5. Security Issues
        self.check_security_issues()
        
        # 6. Performance Issues
        self.check_performance_issues()

    def check_environment_config(self):
        """Check environment configuration issues"""
        self.stdout.write('\n1. Environment Configuration:')
        
        # Check DEBUG setting
        if settings.DEBUG:
            self.stdout.write(self.style.WARNING('  ⚠ DEBUG is True - This should be False in production'))
        else:
            self.stdout.write('  ✓ DEBUG is False (correct for production)')
        
        # Check SECRET_KEY
        if settings.SECRET_KEY == 'django-insecure-please-change-this-key':
            self.stdout.write(self.style.ERROR('  ✗ SECRET_KEY is default - Change this immediately!'))
        else:
            self.stdout.write('  ✓ SECRET_KEY is set')
        
        # Check ALLOWED_HOSTS
        if not settings.ALLOWED_HOSTS:
            self.stdout.write(self.style.ERROR('  ✗ ALLOWED_HOSTS is empty'))
        elif 'papersetu2.onrender.com' in settings.ALLOWED_HOSTS:
            self.stdout.write('  ✓ ALLOWED_HOSTS includes papersetu2.onrender.com')
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠ ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}'))
        
        # Check database configuration
        db_engine = settings.DATABASES['default']['ENGINE']
        if 'postgresql' in db_engine:
            self.stdout.write('  ✓ Using PostgreSQL (production)')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ Using SQLite (development database)'))

    def check_database_issues(self):
        """Check database connectivity and issues"""
        self.stdout.write('\n2. Database Issues:')
        
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write('  ✓ Database connection successful')
            
            # Check if tables exist
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['accounts_user', 'conference_conference', 'django_migrations']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    self.stdout.write(self.style.ERROR(f'  ✗ Missing tables: {missing_tables}'))
                else:
                    self.stdout.write('  ✓ All required tables exist')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Database error: {e}'))

    def check_static_files_issues(self):
        """Check static files configuration"""
        self.stdout.write('\n3. Static Files Issues:')
        
        # Check static files configuration
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            self.stdout.write(f'  ✓ STATIC_ROOT: {settings.STATIC_ROOT}')
            
            # Check if static files directory exists
            if os.path.exists(settings.STATIC_ROOT):
                self.stdout.write('  ✓ Static files directory exists')
                
                # Check for admin static files
                admin_static = os.path.join(settings.STATIC_ROOT, 'admin')
                if os.path.exists(admin_static):
                    self.stdout.write('  ✓ Admin static files exist')
                    
                    # Check key admin files
                    key_files = ['css/base.css', 'js/core.js']
                    for file_path in key_files:
                        full_path = os.path.join(admin_static, file_path)
                        if os.path.exists(full_path):
                            self.stdout.write(f'    ✓ {file_path}')
                        else:
                            self.stdout.write(self.style.WARNING(f'    ⚠ Missing: {file_path}'))
                else:
                    self.stdout.write(self.style.ERROR('  ✗ Admin static files missing'))
            else:
                self.stdout.write(self.style.ERROR('  ✗ Static files directory missing'))
        else:
            self.stdout.write(self.style.ERROR('  ✗ STATIC_ROOT not configured'))

    def check_authentication_issues(self):
        """Check authentication configuration"""
        self.stdout.write('\n4. Authentication Issues:')
        
        # Check authentication backends
        if hasattr(settings, 'AUTHENTICATION_BACKENDS'):
            self.stdout.write(f'  ✓ Authentication backends: {len(settings.AUTHENTICATION_BACKENDS)}')
            for backend in settings.AUTHENTICATION_BACKENDS:
                self.stdout.write(f'    - {backend}')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ No custom authentication backends'))
        
        # Check user model
        if hasattr(settings, 'AUTH_USER_MODEL'):
            self.stdout.write(f'  ✓ Custom user model: {settings.AUTH_USER_MODEL}')
        else:
            self.stdout.write('  ✓ Using default user model')
        
        # Check if users can login
        try:
            users = User.objects.all()
            active_users = users.filter(is_active=True)
            self.stdout.write(f'  ✓ Total users: {users.count()}, Active: {active_users.count()}')
            
            # Check for users with login issues
            users_without_password = users.filter(password='')
            if users_without_password.exists():
                self.stdout.write(self.style.WARNING(f'  ⚠ Users without password: {users_without_password.count()}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ User model error: {e}'))

    def check_security_issues(self):
        """Check security configuration"""
        self.stdout.write('\n5. Security Issues:')
        
        # Check CSRF settings
        if hasattr(settings, 'CSRF_COOKIE_SECURE'):
            if settings.CSRF_COOKIE_SECURE:
                self.stdout.write('  ✓ CSRF cookie secure')
            else:
                self.stdout.write(self.style.WARNING('  ⚠ CSRF cookie not secure'))
        
        # Check session settings
        if hasattr(settings, 'SESSION_COOKIE_SECURE'):
            if settings.SESSION_COOKIE_SECURE:
                self.stdout.write('  ✓ Session cookie secure')
            else:
                self.stdout.write(self.style.WARNING('  ⚠ Session cookie not secure'))
        
        # Check HTTPS settings
        if hasattr(settings, 'SECURE_SSL_REDIRECT'):
            if settings.SECURE_SSL_REDIRECT:
                self.stdout.write('  ✓ SSL redirect enabled')
            else:
                self.stdout.write(self.style.WARNING('  ⚠ SSL redirect not enabled'))

    def check_performance_issues(self):
        """Check performance configuration"""
        self.stdout.write('\n6. Performance Issues:')
        
        # Check cache configuration
        if hasattr(settings, 'CACHES'):
            self.stdout.write('  ✓ Cache configured')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ No cache configured'))
        
        # Check static files storage
        if hasattr(settings, 'STATICFILES_STORAGE'):
            self.stdout.write(f'  ✓ Static files storage: {settings.STATICFILES_STORAGE}')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ No static files storage configured'))

    def check_specific_url(self, url):
        """Check a specific URL for issues"""
        self.stdout.write(f'\n=== Checking URL: {url} ===')
        
        try:
            response = requests.get(url, timeout=10)
            self.stdout.write(f'Status Code: {response.status_code}')
            
            if response.status_code == 200:
                self.stdout.write('  ✓ URL is accessible')
            elif response.status_code == 404:
                self.stdout.write(self.style.ERROR('  ✗ URL not found (404)'))
            elif response.status_code == 500:
                self.stdout.write(self.style.ERROR('  ✗ Server error (500)'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ Unexpected status: {response.status_code}'))
                
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Request failed: {e}'))

    def fix_common_issues(self):
        """Fix common deployment issues automatically"""
        self.stdout.write('=== Fixing Common Issues ===')
        
        # 1. Collect static files
        self.stdout.write('\n1. Collecting static files...')
        try:
            from django.core.management import call_command
            call_command('collectstatic', '--no-input', '--clear')
            self.stdout.write('  ✓ Static files collected')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Static files error: {e}'))
        
        # 2. Run migrations
        self.stdout.write('\n2. Running migrations...')
        try:
            call_command('migrate')
            self.stdout.write('  ✓ Migrations completed')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Migration error: {e}'))
        
        # 3. Setup admin interface
        self.stdout.write('\n3. Setting up admin interface...')
        try:
            call_command('setup_admin_interface')
            self.stdout.write('  ✓ Admin interface configured')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Admin interface error: {e}'))
        
        # 4. Fix user permissions
        self.stdout.write('\n4. Fixing user permissions...')
        try:
            call_command('fix_user_permissions', '--fix-all')
            self.stdout.write('  ✓ User permissions fixed')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ User permissions error: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Common Issues Fixed ===')) 