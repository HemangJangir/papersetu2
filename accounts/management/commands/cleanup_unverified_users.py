from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from datetime import timedelta

class Command(BaseCommand):
    help = 'Clean up unverified users who have not completed OTP verification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days after which unverified users should be deleted (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find unverified users created before the cutoff date
        unverified_users = User.objects.filter(
            is_verified=False,
            date_joined__lt=cutoff_date
        )
        
        count = unverified_users.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} unverified users created before {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}'
                )
            )
            
            if count > 0:
                self.stdout.write('Users that would be deleted:')
                for user in unverified_users[:10]:  # Show first 10
                    self.stdout.write(f'  - {user.email} (created: {user.date_joined})')
                if count > 10:
                    self.stdout.write(f'  ... and {count - 10} more')
        else:
            if count > 0:
                # Delete the users
                unverified_users.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted {count} unverified users created before {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('No unverified users to delete.')
                ) 