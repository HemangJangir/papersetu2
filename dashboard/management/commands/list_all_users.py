from django.core.management.base import BaseCommand
from accounts.models import User
from conference.models import Conference, Paper
from django.db.models import Count
from datetime import datetime

class Command(BaseCommand):
    help = 'List all users in the database with detailed information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active',
            action='store_true',
            help='Show only active users',
        )
        parser.add_argument(
            '--verified',
            action='store_true',
            help='Show only verified users',
        )
        parser.add_argument(
            '--recent',
            type=int,
            help='Show only users registered in the last N days',
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 80)
        self.stdout.write('USER DATABASE REPORT')
        self.stdout.write('=' * 80)
        
        # Get users with related data
        users = User.objects.prefetch_related('conference_set', 'paper_set')
        
        # Apply filters
        if options['active']:
            users = users.filter(is_active=True)
        
        if options['verified']:
            users = users.filter(is_verified=True)
        
        if options['recent']:
            from datetime import timedelta
            from django.utils import timezone
            cutoff_date = timezone.now() - timedelta(days=options['recent'])
            users = users.filter(date_joined__gte=cutoff_date)
        
        # Get statistics
        total_users = users.count()
        active_users = users.filter(is_active=True).count()
        verified_users = users.filter(is_verified=True).count()
        staff_users = users.filter(is_staff=True).count()
        superusers = users.filter(is_superuser=True).count()
        
        self.stdout.write(f'\n📊 SUMMARY STATISTICS:')
        self.stdout.write(f'   Total Users: {total_users}')
        self.stdout.write(f'   Active: {active_users}')
        self.stdout.write(f'   Verified: {verified_users}')
        self.stdout.write(f'   Staff: {staff_users}')
        self.stdout.write(f'   Superusers: {superusers}')
        
        # Get users who created conferences
        conference_creators = users.filter(conference__isnull=False).distinct().count()
        paper_authors = users.filter(paper__isnull=False).distinct().count()
        
        self.stdout.write(f'   Conference Creators: {conference_creators}')
        self.stdout.write(f'   Paper Authors: {paper_authors}')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('DETAILED USER LIST')
        self.stdout.write('=' * 80)
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found matching the criteria.'))
            return
        
        for i, user in enumerate(users, 1):
            self.stdout.write(f'\n{i}. {user.get_full_name() or user.username}')
            self.stdout.write('   ' + '-' * (len(user.get_full_name() or user.username) + 2))
            
            # Basic info
            self.stdout.write(f'   Username: {user.username}')
            self.stdout.write(f'   Email: {user.email}')
            self.stdout.write(f'   First Name: {user.first_name or "Not provided"}')
            self.stdout.write(f'   Last Name: {user.last_name or "Not provided"}')
            
            # Status
            self.stdout.write(f'   Active: {"✓ Yes" if user.is_active else "✗ No"}')
            self.stdout.write(f'   Verified: {"✓ Yes" if user.is_verified else "✗ No"}')
            self.stdout.write(f'   Staff: {"✓ Yes" if user.is_staff else "✗ No"}')
            self.stdout.write(f'   Superuser: {"✓ Yes" if user.is_superuser else "✗ No"}')
            
            # Dates
            self.stdout.write(f'   Date Joined: {user.date_joined.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write(f'   Last Login: {user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"}')
            
            # Activity
            conference_count = user.conference_set.count()
            paper_count = user.paper_set.count()
            
            self.stdout.write(f'   Conferences Created: {conference_count}')
            self.stdout.write(f'   Papers Submitted: {paper_count}')
            
            # Show conferences if any
            if conference_count > 0:
                self.stdout.write(f'   Conference List:')
                for conf in user.conference_set.all()[:3]:  # Show first 3
                    status_icon = "✓" if conf.is_approved else "⏳"
                    self.stdout.write(f'     {status_icon} {conf.acronym} ({conf.status}) - {conf.name[:50]}...')
                if conference_count > 3:
                    self.stdout.write(f'     ... and {conference_count - 3} more')
            
            # Show papers if any
            if paper_count > 0:
                self.stdout.write(f'   Recent Papers:')
                for paper in user.paper_set.all()[:3]:  # Show first 3
                    self.stdout.write(f'     📄 {paper.title[:50]}... ({paper.conference.acronym})')
                if paper_count > 3:
                    self.stdout.write(f'     ... and {paper_count - 3} more')
            
            # Admin links
            self.stdout.write(f'   Admin Links:')
            self.stdout.write(f'     - Edit User: /admin/accounts/user/{user.id}/change/')
            if conference_count > 0:
                self.stdout.write(f'     - User Conferences: /admin/conference/conference/?chair__id__exact={user.id}')
            if paper_count > 0:
                self.stdout.write(f'     - User Papers: /admin/conference/paper/?author__id__exact={user.id}')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('RECENT REGISTRATIONS (Last 10 Users)')
        self.stdout.write('=' * 80)
        
        recent_users = users.order_by('-date_joined')[:10]
        
        for user in recent_users:
            user_name = user.get_full_name() or user.username
            conference_count = user.conference_set.count()
            paper_count = user.paper_set.count()
            activity = []
            if conference_count > 0:
                activity.append(f"{conference_count} conf")
            if paper_count > 0:
                activity.append(f"{paper_count} papers")
            
            activity_str = f" ({', '.join(activity)})" if activity else ""
            self.stdout.write(f'{user.date_joined.strftime("%Y-%m-%d %H:%M")} - {user_name}{activity_str}')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('ADMIN ACTIONS')
        self.stdout.write('=' * 80)
        self.stdout.write('To view in admin interface:')
        self.stdout.write('  http://your-domain.com/admin/accounts/user/')
        self.stdout.write('\nTo verify all users:')
        self.stdout.write('  python manage.py shell')
        self.stdout.write('  >>> from accounts.models import User')
        self.stdout.write('  >>> User.objects.filter(is_verified=False).update(is_verified=True)')
        self.stdout.write('=' * 80) 