from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix user permissions and remove inappropriate admin access'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Specific username to fix'
        )
        parser.add_argument(
            '--fix-all',
            action='store_true',
            help='Fix all users with inappropriate permissions'
        )

    def handle(self, *args, **options):
        if options.get('username'):
            self.fix_specific_user(options['username'])
        elif options.get('fix_all'):
            self.fix_all_users()
        else:
            self.show_user_permissions()

    def show_user_permissions(self):
        """Show current user permissions"""
        self.stdout.write(self.style.SUCCESS('=== Current User Permissions ==='))
        
        users = User.objects.all()
        for user in users:
            status = []
            if user.is_superuser:
                status.append('👑 Superuser')
            if user.is_staff:
                status.append('👤 Staff')
            if user.is_active:
                status.append('✅ Active')
            else:
                status.append('❌ Inactive')
            if user.is_verified:
                status.append('✓ Verified')
            else:
                status.append('⚠ Unverified')
            
            self.stdout.write(f'{user.username} ({user.email}): {", ".join(status)}')

    def fix_specific_user(self, username):
        """Fix permissions for a specific user"""
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f'Fixing permissions for {username}...')
            
            # Check if this user should have admin access
            if username in ['admin', 'PaperSetu']:  # Legitimate admin users
                self.stdout.write(f'  ✓ {username} is a legitimate admin user')
                return
            
            # Remove staff and superuser status for non-admin users
            if user.is_staff or user.is_superuser:
                user.is_staff = False
                user.is_superuser = False
                user.save()
                self.stdout.write(f'  ✓ Removed admin access from {username}')
            else:
                self.stdout.write(f'  ✓ {username} already has correct permissions')
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))

    def fix_all_users(self):
        """Fix permissions for all users"""
        self.stdout.write('=== Fixing All User Permissions ===')
        
        users = User.objects.all()
        fixed_count = 0
        
        for user in users:
            # Skip legitimate admin users
            if user.username in ['admin', 'PaperSetu']:
                self.stdout.write(f'  ✓ Skipping legitimate admin: {user.username}')
                continue
            
            # Remove staff and superuser status for conference chairs and regular users
            if user.is_staff or user.is_superuser:
                user.is_staff = False
                user.is_superuser = False
                user.save()
                self.stdout.write(f'  ✓ Fixed {user.username}: Removed admin access')
                fixed_count += 1
            else:
                self.stdout.write(f'  ✓ {user.username}: Already has correct permissions')
        
        self.stdout.write(self.style.SUCCESS(f'Fixed permissions for {fixed_count} users'))

    def create_proper_admin(self):
        """Create a proper admin user"""
        self.stdout.write('=== Creating Proper Admin User ===')
        
        # Check if admin already exists
        if User.objects.filter(username='admin').exists():
            self.stdout.write('  ✓ Admin user already exists')
            return
        
        # Create admin user
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@papersetu.com',
            password='admin123'
        )
        
        self.stdout.write(self.style.SUCCESS('  ✓ Created admin user: admin/admin123')) 