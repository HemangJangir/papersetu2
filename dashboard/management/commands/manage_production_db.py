from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from conference.models import Conference, UserConferenceRole
from django.db import connection
import os
import sys

User = get_user_model()

class Command(BaseCommand):
    help = 'Manage production database operations'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'backup', 'restore', 'sync', 'create_superuser', 'reset_passwords', 'check_users'],
            help='Action to perform'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username for superuser creation'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for superuser creation'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for superuser creation'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'status':
            self.show_status()
        elif action == 'backup':
            self.backup_database()
        elif action == 'restore':
            self.restore_database()
        elif action == 'sync':
            self.sync_data()
        elif action == 'create_superuser':
            self.create_superuser(options)
        elif action == 'reset_passwords':
            self.reset_passwords()
        elif action == 'check_users':
            self.check_users()

    def show_status(self):
        """Show database and application status"""
        self.stdout.write(self.style.SUCCESS('=== Production Database Status ==='))
        
        # Database info
        db_engine = settings.DATABASES['default']['ENGINE']
        self.stdout.write(f'Database Engine: {db_engine}')
        
        if 'postgresql' in db_engine:
            self.stdout.write('✓ Using PostgreSQL (Production)')
        else:
            self.stdout.write('⚠ Using SQLite (Development)')
        
        # Application stats
        try:
            user_count = User.objects.count()
            conference_count = Conference.objects.count()
            approved_conferences = Conference.objects.filter(is_approved=True).count()
            
            self.stdout.write(f'\nApplication Statistics:')
            self.stdout.write(f'  Users: {user_count}')
            self.stdout.write(f'  Conferences: {conference_count}')
            self.stdout.write(f'  Approved Conferences: {approved_conferences}')
            
            # List recent conferences
            self.stdout.write(f'\nRecent Conferences:')
            for conf in Conference.objects.order_by('-created_at')[:5]:
                status = "✓" if conf.is_approved else "⚠"
                self.stdout.write(f'  {status} {conf.name} (ID: {conf.id})')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error accessing database: {e}'))

    def backup_database(self):
        """Backup database (PostgreSQL only)"""
        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            self.stdout.write(self.style.WARNING('Backup only available for PostgreSQL'))
            return
            
        try:
            import subprocess
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                self.stdout.write(self.style.ERROR('DATABASE_URL not found'))
                return
                
            # Extract database info from URL
            import dj_database_url
            db_config = dj_database_url.parse(db_url)
            
            backup_file = f'backup_{db_config["NAME"]}_{settings.TIME_ZONE}.sql'
            
            # Create backup command
            cmd = [
                'pg_dump',
                f'--host={db_config["HOST"]}',
                f'--port={db_config["PORT"]}',
                f'--username={db_config["USER"]}',
                f'--dbname={db_config["NAME"]}',
                '--no-password',
                f'--file={backup_file}'
            ]
            
            # Set password environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS(f'Backup created: {backup_file}'))
            else:
                self.stdout.write(self.style.ERROR(f'Backup failed: {result.stderr}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Backup error: {e}'))

    def create_superuser(self, options):
        """Create a superuser"""
        username = options.get('username') or 'admin'
        email = options.get('email') or 'admin@papersetu.com'
        password = options.get('password') or 'admin123'
        
        try:
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'User {username} already exists'))
                return
                
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser created successfully:\n'
                    f'  Username: {username}\n'
                    f'  Email: {email}\n'
                    f'  Password: {password}'
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {e}'))

    def reset_passwords(self):
        """Reset all user passwords to default"""
        try:
            default_password = 'changeme123'
            users = User.objects.all()
            
            for user in users:
                user.set_password(default_password)
                user.save()
                
            self.stdout.write(
                self.style.SUCCESS(
                    f'Reset {users.count()} user passwords to: {default_password}'
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error resetting passwords: {e}'))

    def check_users(self):
        """Check user accounts and their status"""
        try:
            users = User.objects.all()
            
            self.stdout.write(f'\n=== User Account Status ===')
            self.stdout.write(f'Total Users: {users.count()}')
            
            superusers = users.filter(is_superuser=True)
            self.stdout.write(f'Superusers: {superusers.count()}')
            
            staff_users = users.filter(is_staff=True)
            self.stdout.write(f'Staff Users: {staff_users.count()}')
            
            active_users = users.filter(is_active=True)
            self.stdout.write(f'Active Users: {active_users.count()}')
            
            # Show recent users
            self.stdout.write(f'\nRecent Users:')
            for user in users.order_by('-date_joined')[:10]:
                status = "✓" if user.is_active else "✗"
                staff = "👑" if user.is_superuser else "👤" if user.is_staff else "👥"
                self.stdout.write(f'  {status} {staff} {user.username} ({user.email}) - {user.date_joined.strftime("%Y-%m-%d")}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking users: {e}'))

    def sync_data(self):
        """Sync data between environments"""
        self.stdout.write('Data synchronization would be implemented here')
        self.stdout.write('This could include:')
        self.stdout.write('- Export/import conference data')
        self.stdout.write('- User account synchronization')
        self.stdout.write('- Configuration synchronization') 