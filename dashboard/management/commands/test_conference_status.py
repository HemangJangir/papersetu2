from django.core.management.base import BaseCommand
from conference.models import Conference
from django.utils import timezone

class Command(BaseCommand):
    help = 'Test conference status logic'

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write(f"Today's date: {today}")
        
        conferences = Conference.objects.filter(
            is_approved=True,
            status__in=['upcoming', 'live']
        ).order_by('start_date')[:5]
        
        self.stdout.write(f"Found {conferences.count()} conferences:")
        
        for conference in conferences:
            # Check if conference is currently ongoing
            is_ongoing = conference.start_date <= today <= conference.end_date
            
            self.stdout.write(
                f"- {conference.name} ({conference.acronym})"
                f"\n  Status: {conference.status}"
                f"\n  Start: {conference.start_date}"
                f"\n  End: {conference.end_date}"
                f"\n  Is Ongoing: {is_ongoing}"
                f"\n  Display Status: {'Ongoing' if is_ongoing else conference.status.title()}"
                f"\n"
            ) 