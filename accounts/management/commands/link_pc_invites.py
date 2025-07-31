from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from conference.models import PCInvite, UserConferenceRole
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Link PC invites to existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Specific email to process',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        email = options.get('email')
        dry_run = options.get('dry_run')
        
        if email:
            # Process specific email
            self.process_email(email, dry_run)
        else:
            # Process all PC invites
            self.process_all_pc_invites(dry_run)

    def process_email(self, email, dry_run=False):
        """Process PC invites for a specific email"""
        try:
            user = User.objects.get(email=email)
            pc_invites = PCInvite.objects.filter(email=email)
            
            if not pc_invites.exists():
                self.stdout.write(f"No PC invites found for {email}")
                return
            
            self.stdout.write(f"Found {pc_invites.count()} PC invites for {email}")
            
            for invite in pc_invites:
                if dry_run:
                    self.stdout.write(f"Would link invite for {invite.conference.name} (status: {invite.status}) to user {user.username}")
                else:
                    self.link_invite_to_user(invite, user)
                    
        except User.DoesNotExist:
            self.stdout.write(f"No user found with email {email}")
        except Exception as e:
            self.stdout.write(f"Error processing {email}: {str(e)}")

    def process_all_pc_invites(self, dry_run=False):
        """Process all PC invites"""
        pc_invites = PCInvite.objects.all()
        
        if not pc_invites.exists():
            self.stdout.write("No PC invites found")
            return
        
        self.stdout.write(f"Found {pc_invites.count()} PC invites")
        
        processed_count = 0
        for invite in pc_invites:
            try:
                user = User.objects.get(email=invite.email)
                if dry_run:
                    self.stdout.write(f"Would link invite for {invite.conference.name} (status: {invite.status}) to user {user.username}")
                else:
                    self.link_invite_to_user(invite, user)
                processed_count += 1
            except User.DoesNotExist:
                self.stdout.write(f"No user found for invite email: {invite.email}")
            except Exception as e:
                self.stdout.write(f"Error processing invite {invite.id}: {str(e)}")
        
        if not dry_run:
            self.stdout.write(f"Successfully processed {processed_count} invites")

    def link_invite_to_user(self, invite, user):
        """Link a PC invite to a user"""
        if invite.status == 'pending':
            # Auto-accept pending invites
            invite.status = 'accepted'
            invite.accepted_at = timezone.now()
            invite.save()
            self.stdout.write(f"Auto-accepted pending invite for {user.username} in {invite.conference.name}")
        
        # Create UserConferenceRole
        role, created = UserConferenceRole.objects.get_or_create(
            user=user,
            conference=invite.conference,
            role='pc_member',
            track=invite.track
        )
        
        if created:
            self.stdout.write(f"Created PC member role for {user.username} in {invite.conference.name}")
        else:
            self.stdout.write(f"PC member role already exists for {user.username} in {invite.conference.name}")
        
        # Send notification to chair for newly accepted invites
        if invite.status == 'accepted' and invite.accepted_at:
            try:
                from conference.models import Notification
                Notification.objects.create(
                    recipient=invite.invited_by,
                    notification_type='reviewer_response',
                    title=f'PC Member Accepted Invitation',
                    message=f'{user.get_full_name()} ({user.email}) has accepted the PC member invitation for {invite.conference.name}.',
                    related_conference=invite.conference
                )
            except Exception as e:
                self.stdout.write(f"Could not create notification: {str(e)}") 