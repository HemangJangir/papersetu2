from django.core.management.base import BaseCommand
from conference.models import Conference
from django.db.models import Count
from datetime import datetime

class Command(BaseCommand):
    help = 'List all conferences in the database with detailed information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            type=str,
            help='Filter by status (upcoming, live, completed, cancelled)',
        )
        parser.add_argument(
            '--approved',
            action='store_true',
            help='Show only approved conferences',
        )
        parser.add_argument(
            '--pending',
            action='store_true',
            help='Show only pending conferences',
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 80)
        self.stdout.write('CONFERENCE DATABASE REPORT')
        self.stdout.write('=' * 80)
        
        # Get conferences with related data
        conferences = Conference.objects.select_related('chair').prefetch_related('papers', 'userconferencerole_set')
        
        # Apply filters
        if options['status']:
            conferences = conferences.filter(status=options['status'])
        
        if options['approved']:
            conferences = conferences.filter(is_approved=True)
        
        if options['pending']:
            conferences = conferences.filter(is_approved=False)
        
        # Get statistics
        total_conferences = conferences.count()
        approved_conferences = conferences.filter(is_approved=True).count()
        pending_conferences = conferences.filter(is_approved=False).count()
        
        # Status breakdown
        status_counts = conferences.values('status').annotate(count=Count('id'))
        
        self.stdout.write(f'\n📊 SUMMARY STATISTICS:')
        self.stdout.write(f'   Total Conferences: {total_conferences}')
        self.stdout.write(f'   Approved: {approved_conferences}')
        self.stdout.write(f'   Pending: {pending_conferences}')
        
        self.stdout.write(f'\n📈 STATUS BREAKDOWN:')
        for status in status_counts:
            self.stdout.write(f'   {status["status"].title()}: {status["count"]}')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('DETAILED CONFERENCE LIST')
        self.stdout.write('=' * 80)
        
        if not conferences.exists():
            self.stdout.write(self.style.WARNING('No conferences found matching the criteria.'))
            return
        
        for i, conference in enumerate(conferences, 1):
            self.stdout.write(f'\n{i}. {conference.name}')
            self.stdout.write('   ' + '-' * (len(conference.name) + 2))
            
            # Basic info
            self.stdout.write(f'   Acronym: {conference.acronym}')
            self.stdout.write(f'   Status: {conference.status.title()}')
            self.stdout.write(f'   Approved: {"✓ Yes" if conference.is_approved else "✗ No"}')
            
            # Chair info
            if conference.chair:
                chair_name = conference.chair.get_full_name() or conference.chair.username
                self.stdout.write(f'   Chair: {chair_name} ({conference.chair.email})')
                self.stdout.write(f'   Chair Joined: {conference.chair.date_joined.strftime("%Y-%m-%d %H:%M")}')
                self.stdout.write(f'   Chair Last Login: {conference.chair.last_login.strftime("%Y-%m-%d %H:%M") if conference.chair.last_login else "Never"}')
                self.stdout.write(f'   Chair Active: {"✓ Yes" if conference.chair.is_active else "✗ No"}')
            else:
                self.stdout.write('   Chair: Not assigned')
            
            # Dates
            self.stdout.write(f'   Start Date: {conference.start_date}')
            self.stdout.write(f'   End Date: {conference.end_date}')
            if conference.paper_submission_deadline:
                self.stdout.write(f'   Submission Deadline: {conference.paper_submission_deadline}')
            
            # Venue
            self.stdout.write(f'   Venue: {conference.venue}, {conference.city}, {conference.country}')
            
            # Statistics
            paper_count = conference.papers.count()
            user_count = conference.userconferencerole_set.count()
            
            self.stdout.write(f'   Papers: {paper_count}')
            self.stdout.write(f'   Users: {user_count}')
            
            # Contact info
            if conference.contact_email:
                self.stdout.write(f'   Contact: {conference.contact_email}')
            if conference.web_page:
                self.stdout.write(f'   Website: {conference.web_page}')
            
            # Created date
            if hasattr(conference, 'created_at') and conference.created_at:
                self.stdout.write(f'   Created: {conference.created_at.strftime("%Y-%m-%d %H:%M")}')
            
            # Admin links
            self.stdout.write(f'   Admin Links:')
            self.stdout.write(f'     - Edit: /admin/conference/conference/{conference.id}/change/')
            self.stdout.write(f'     - Papers: /admin/conference/paper/?conference__id__exact={conference.id}')
            self.stdout.write(f'     - Users: /admin/conference/userconferencerole/?conference__id__exact={conference.id}')
            self.stdout.write(f'     - Manage: /dashboard/conference_submissions/{conference.id}/')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('RECENT ACTIVITY (Last 10 Conferences)')
        self.stdout.write('=' * 80)
        
        recent_conferences = conferences.order_by('-created_at' if hasattr(Conference, 'created_at') else '-id')[:10]
        
        for conference in recent_conferences:
            created_date = conference.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(conference, 'created_at') and conference.created_at else "Unknown"
            chair_name = conference.chair.get_full_name() or conference.chair.username if conference.chair else "No chair"
            self.stdout.write(f'{created_date} - {conference.acronym} ({conference.status}) by {chair_name}')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('ADMIN ACTIONS')
        self.stdout.write('=' * 80)
        self.stdout.write('To approve pending conferences:')
        self.stdout.write('  python manage.py shell')
        self.stdout.write('  >>> from conference.models import Conference')
        self.stdout.write('  >>> Conference.objects.filter(is_approved=False).update(is_approved=True)')
        self.stdout.write('\nTo view in admin interface:')
        self.stdout.write('  http://your-domain.com/admin/conference/conference/')
        self.stdout.write('=' * 80) 