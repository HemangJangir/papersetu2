from django.core.management.base import BaseCommand
from django.urls import reverse, NoReverseMatch

class Command(BaseCommand):
    help = 'Test URL patterns to ensure they resolve correctly'

    def handle(self, *args, **options):
        self.stdout.write("Testing URL patterns...")
        
        # Test the problematic URL
        try:
            url = reverse('conference:join_conference_redirect', kwargs={'conference_id': 1})
            self.stdout.write(self.style.SUCCESS(f"✅ join_conference_redirect URL resolves: {url}"))
        except NoReverseMatch as e:
            self.stdout.write(self.style.ERROR(f"❌ join_conference_redirect URL failed: {e}"))
        
        # Test other important URLs
        urls_to_test = [
            ('conference:browse_conferences', {}),
            ('conference:choose_conference_role', {'conference_id': 1}),
            ('accounts:login', {}),
            ('homepage', {}),
        ]
        
        for url_name, kwargs in urls_to_test:
            try:
                url = reverse(url_name, kwargs=kwargs)
                self.stdout.write(self.style.SUCCESS(f"✅ {url_name} resolves: {url}"))
            except NoReverseMatch as e:
                self.stdout.write(self.style.ERROR(f"❌ {url_name} failed: {e}"))
        
        self.stdout.write(self.style.SUCCESS("URL testing completed!")) 