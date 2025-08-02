from django.core.management.base import BaseCommand
from conference.models import Conference
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check available conferences for the landing page'

    def handle(self, *args, **options):
        conferences = Conference.objects.filter(
            is_approved=True,
            status__in=['upcoming', 'live']
        ).order_by('start_date')[:10]
        
        self.stdout.write(f"Found {conferences.count()} conferences for landing page:")
        
        for conference in conferences:
            self.stdout.write(
                f"- {conference.name} ({conference.acronym}) - {conference.status} - {conference.start_date}"
            )
        
        if conferences.count() == 0:
            self.stdout.write(
                self.style.WARNING("No conferences found! The landing page will show the 'No Conferences Available' message.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Conferences are available for the landing page!")
            ) 