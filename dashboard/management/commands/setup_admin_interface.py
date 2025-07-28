from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup admin interface with proper styling and configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Setting up Admin Interface ==='))
        
        # Check if admin_interface is installed
        try:
            from admin_interface.models import Theme
            self.stdout.write('✓ Admin interface is installed')
        except ImportError:
            self.stdout.write(self.style.ERROR('✗ Admin interface not installed. Please install django-admin-interface'))
            return
        
        # Create or update theme
        try:
            theme, created = Theme.objects.get_or_create(
                name='PaperSetu Theme',
                defaults={
                    'title': 'PaperSetu Administration',
                    'logo': 'https://img.icons8.com/color/48/000000/conference.png',
                    'logo_color': '#2E86AB',
                    'title_color': '#2E86AB',
                    'css_header_background_color': '#2E86AB',
                    'css_header_text_color': '#FFFFFF',
                    'css_header_link_color': '#FFFFFF',
                    'css_header_link_hover_color': '#1A5F7A',
                    'css_module_background_color': '#F8F9FA',
                    'css_module_text_color': '#2E86AB',
                    'css_module_link_color': '#2E86AB',
                    'css_module_link_hover_color': '#1A5F7A',
                    'css_generic_link_color': '#2E86AB',
                    'css_generic_link_hover_color': '#1A5F7A',
                    'css_save_button_background_color': '#28A745',
                    'css_save_button_background_hover_color': '#218838',
                    'css_delete_button_background_color': '#DC3545',
                    'css_delete_button_background_hover_color': '#C82333',
                }
            )
            
            if created:
                self.stdout.write('✓ Created PaperSetu theme')
            else:
                # Update existing theme
                theme.title = 'PaperSetu Administration'
                theme.logo = 'https://img.icons8.com/color/48/000000/conference.png'
                theme.logo_color = '#2E86AB'
                theme.title_color = '#2E86AB'
                theme.css_header_background_color = '#2E86AB'
                theme.css_header_text_color = '#FFFFFF'
                theme.css_header_link_color = '#FFFFFF'
                theme.css_header_link_hover_color = '#1A5F7A'
                theme.css_module_background_color = '#F8F9FA'
                theme.css_module_text_color = '#2E86AB'
                theme.css_module_link_color = '#2E86AB'
                theme.css_module_link_hover_color = '#1A5F7A'
                theme.css_generic_link_color = '#2E86AB'
                theme.css_generic_link_hover_color = '#1A5F7A'
                theme.css_save_button_background_color = '#28A745'
                theme.css_save_button_background_hover_color = '#218838'
                theme.css_delete_button_background_color = '#DC3545'
                theme.css_delete_button_background_hover_color = '#C82333'
                theme.save()
                self.stdout.write('✓ Updated PaperSetu theme')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error setting up theme: {e}'))
        
        # Check static files
        self.stdout.write('\n=== Checking Static Files ===')
        static_root = settings.STATIC_ROOT
        admin_static = os.path.join(static_root, 'admin')
        
        if os.path.exists(static_root):
            self.stdout.write(f'✓ Static root exists: {static_root}')
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Static root missing: {static_root}'))
            
        if os.path.exists(admin_static):
            self.stdout.write(f'✓ Admin static files exist: {admin_static}')
            
            # Check for key admin files
            key_files = [
                'css/base.css',
                'css/dashboard.css',
                'css/forms.css',
                'css/changelists.css',
                'js/core.js',
                'js/admin/RelatedObjectLookups.js'
            ]
            
            for file_path in key_files:
                full_path = os.path.join(admin_static, file_path)
                if os.path.exists(full_path):
                    self.stdout.write(f'  ✓ {file_path}')
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Missing: {file_path}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Admin static files missing: {admin_static}'))
        
        # Check admin site configuration
        self.stdout.write('\n=== Admin Site Configuration ===')
        self.stdout.write(f'✓ Site Header: {settings.ADMIN_SITE_HEADER}')
        self.stdout.write(f'✓ Site Title: {settings.ADMIN_SITE_TITLE}')
        self.stdout.write(f'✓ Index Title: {settings.ADMIN_INDEX_TITLE}')
        
        # Check superuser
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            self.stdout.write(f'✓ Superusers: {superusers.count()}')
            for user in superusers:
                self.stdout.write(f'  - {user.username} ({user.email})')
        else:
            self.stdout.write(self.style.WARNING('⚠ No superusers found'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Admin Interface Setup Complete ==='))
        self.stdout.write('Admin interface should now be properly styled and configured.') 