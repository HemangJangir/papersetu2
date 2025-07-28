from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from conference.models import Conference
from datetime import date, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Add ICIMMI conference to the database'

    def handle(self, *args, **options):
        self.stdout.write('Adding ICIMMI conference...')
        
        # Check if conference already exists
        if Conference.objects.filter(name__icontains='icimmi').exists():
            self.stdout.write(self.style.WARNING('ICIMMI conference already exists!'))
            return
        
        # Get or create a chair user
        chair, created = User.objects.get_or_create(
            username='icimmi_chair',
            defaults={
                'email': 'chair@icimmi.com',
                'first_name': 'ICIMMI',
                'last_name': 'Chair',
                'is_active': True,
                'is_verified': True,
            }
        )
        
        if created:
            chair.set_password('icimmi123')
            chair.save()
            self.stdout.write(f'Created chair user: {chair.username}')
        
        # Create the conference
        conference = Conference.objects.create(
            name='International Conference on Information Management and Machine Intelligence (ICIMMI)',
            acronym='ICIMMI',
            description='A premier conference focusing on information management and machine intelligence research.',
            theme_domain='Information Management, Machine Intelligence, AI, Data Science',
            chair=chair,
            chair_name='ICIMMI Conference Chair',
            chair_email='chair@icimmi.com',
            organizer='ICIMMI Organizing Committee',
            venue='Virtual Conference',
            city='Online',
            country='Global',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32),
            primary_area='AI',
            secondary_area='ML',
            is_approved=True,
            status='upcoming',
            contact_email='info@icimmi.com',
            web_page='https://icimmi.com',
            paper_submission_deadline=date.today() + timedelta(days=15),
            paper_format='pdf',
            abstract_required=True,
            max_paper_length=10,
            reviewers_per_paper=3,
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created ICIMMI conference (ID: {conference.id})'
            )
        ) 