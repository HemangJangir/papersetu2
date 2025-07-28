from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import make_password
from django.conf import settings
from conference.models import Conference
import re

User = get_user_model()

class Command(BaseCommand):
    help = 'Diagnose and fix common login issues'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['diagnose', 'fix_passwords', 'activate_users', 'check_email', 'test_auth'],
            help='Action to perform'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Specific username to check'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Specific email to check'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'diagnose':
            self.diagnose_login_issues(options)
        elif action == 'fix_passwords':
            self.fix_passwords(options)
        elif action == 'activate_users':
            self.activate_users(options)
        elif action == 'check_email':
            self.check_email_format(options)
        elif action == 'test_auth':
            self.test_authentication(options)

    def diagnose_login_issues(self, options):
        """Diagnose common login issues"""
        self.stdout.write(self.style.SUCCESS('=== Login Issues Diagnosis ==='))
        
        # Check authentication backends
        self.stdout.write('\n1. Authentication Backends:')
        for backend in settings.AUTHENTICATION_BACKENDS:
            self.stdout.write(f'   ✓ {backend}')
        
        # Check user accounts
        self.stdout.write('\n2. User Account Issues:')
        users = User.objects.all()
        
        inactive_users = users.filter(is_active=False)
        unverified_users = users.filter(is_verified=False)
        users_without_password = users.filter(password='')
        
        self.stdout.write(f'   Total Users: {users.count()}')
        self.stdout.write(f'   Inactive Users: {inactive_users.count()}')
        self.stdout.write(f'   Unverified Users: {unverified_users.count()}')
        self.stdout.write(f'   Users without password: {users_without_password.count()}')
        
        # Check for problematic usernames/emails
        self.stdout.write('\n3. Problematic Accounts:')
        for user in users:
            issues = []
            
            if not user.is_active:
                issues.append('Inactive')
            if not user.is_verified:
                issues.append('Unverified')
            if not user.password:
                issues.append('No password')
            if not user.email or '@' not in user.email:
                issues.append('Invalid email')
            if len(user.username) < 3:
                issues.append('Short username')
            
            if issues:
                self.stdout.write(f'   ⚠ {user.username} ({user.email}): {", ".join(issues)}')
        
        # Check specific user if provided
        if options.get('username'):
            self.check_specific_user(options['username'])
        elif options.get('email'):
            self.check_specific_user_by_email(options['email'])

    def check_specific_user(self, username):
        """Check a specific user's login status"""
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f'\n4. User Analysis for {username}:')
            self.stdout.write(f'   Username: {user.username}')
            self.stdout.write(f'   Email: {user.email}')
            self.stdout.write(f'   Active: {user.is_active}')
            self.stdout.write(f'   Verified: {user.is_verified}')
            self.stdout.write(f'   Staff: {user.is_staff}')
            self.stdout.write(f'   Superuser: {user.is_superuser}')
            self.stdout.write(f'   Has password: {bool(user.password)}')
            self.stdout.write(f'   Date joined: {user.date_joined}')
            
            # Test authentication
            auth_user = authenticate(username=username, password='test123')
            if auth_user:
                self.stdout.write(f'   ✓ Authentication works with test password')
            else:
                self.stdout.write(f'   ✗ Authentication failed')
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'   User {username} not found'))

    def check_specific_user_by_email(self, email):
        """Check a specific user by email"""
        try:
            user = User.objects.get(email=email)
            self.check_specific_user(user.username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'   User with email {email} not found'))

    def fix_passwords(self, options):
        """Fix password issues"""
        self.stdout.write('=== Fixing Password Issues ===')
        
        default_password = 'changeme123'
        users = User.objects.all()
        
        if options.get('username'):
            users = users.filter(username=options['username'])
        elif options.get('email'):
            users = users.filter(email=options['email'])
        
        fixed_count = 0
        for user in users:
            if not user.password or len(user.password) < 10:
                user.password = make_password(default_password)
                user.save()
                self.stdout.write(f'   Fixed password for {user.username}')
                fixed_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Fixed passwords for {fixed_count} users'))
        if fixed_count > 0:
            self.stdout.write(f'Default password: {default_password}')

    def activate_users(self, options):
        """Activate inactive users"""
        self.stdout.write('=== Activating Users ===')
        
        users = User.objects.filter(is_active=False)
        
        if options.get('username'):
            users = users.filter(username=options['username'])
        elif options.get('email'):
            users = users.filter(email=options['email'])
        
        activated_count = 0
        for user in users:
            user.is_active = True
            user.is_verified = True
            user.save()
            self.stdout.write(f'   Activated {user.username}')
            activated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Activated {activated_count} users'))

    def check_email_format(self, options):
        """Check email format issues"""
        self.stdout.write('=== Email Format Check ===')
        
        users = User.objects.all()
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        invalid_emails = []
        for user in users:
            if not user.email or not email_pattern.match(user.email):
                invalid_emails.append(user)
        
        self.stdout.write(f'Found {len(invalid_emails)} users with invalid emails:')
        for user in invalid_emails:
            self.stdout.write(f'   {user.username}: {user.email}')

    def test_authentication(self, options):
        """Test authentication for specific user"""
        if not options.get('username'):
            self.stdout.write(self.style.ERROR('Please provide --username to test authentication'))
            return
        
        username = options['username']
        test_password = 'test123'
        
        self.stdout.write(f'=== Testing Authentication for {username} ===')
        
        # Test with username
        user = authenticate(username=username, password=test_password)
        if user:
            self.stdout.write(f'   ✓ Authentication successful with username')
        else:
            self.stdout.write(f'   ✗ Authentication failed with username')
        
        # Test with email if available
        try:
            user_obj = User.objects.get(username=username)
            if user_obj.email:
                email_user = authenticate(username=user_obj.email, password=test_password)
                if email_user:
                    self.stdout.write(f'   ✓ Authentication successful with email')
                else:
                    self.stdout.write(f'   ✗ Authentication failed with email')
        except User.DoesNotExist:
            self.stdout.write(f'   User {username} not found') 