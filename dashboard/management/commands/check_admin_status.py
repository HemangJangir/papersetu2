from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from conference.models import Conference
from django.conf import settings
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Check admin status and database connectivity'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== PaperSetu Admin Status Check ==='))
        
        # Check database
        self.stdout.write('\n1. Database Status:')
        try:
            conference_count = Conference.objects.count()
            user_count = User.objects.count()
            self.stdout.write(f'   ✓ Conferences: {conference_count}')
            self.stdout.write(f'   ✓ Users: {user_count}')
            
            # List all conferences
            self.stdout.write('\n   Conferences in database:')
            for conf in Conference.objects.all()[:10]:
                self.stdout.write(f'   - {conf.name} (ID: {conf.id}, Approved: {conf.is_approved})')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Database error: {e}'))
        
        # Check static files
        self.stdout.write('\n2. Static Files Status:')
        static_root = settings.STATIC_ROOT
        admin_static = os.path.join(static_root, 'admin')
        
        if os.path.exists(static_root):
            self.stdout.write(f'   ✓ Static root exists: {static_root}')
        else:
            self.stdout.write(self.style.WARNING(f'   ⚠ Static root missing: {static_root}'))
            
        if os.path.exists(admin_static):
            self.stdout.write(f'   ✓ Admin static files exist: {admin_static}')
        else:
            self.stdout.write(self.style.WARNING(f'   ⚠ Admin static files missing: {admin_static}'))
        
        # Check environment
        self.stdout.write('\n3. Environment Status:')
        self.stdout.write(f'   DEBUG: {settings.DEBUG}')
        self.stdout.write(f'   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}')
        
        # Check superusers
        self.stdout.write('\n4. Superuser Status:')
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            for user in superusers:
                self.stdout.write(f'   ✓ Superuser: {user.username} ({user.email})')
        else:
            self.stdout.write(self.style.WARNING('   ⚠ No superusers found'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Status Check Complete ===')) 