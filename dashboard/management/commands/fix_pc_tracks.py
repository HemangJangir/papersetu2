from django.core.management.base import BaseCommand
from conference.models import UserConferenceRole, PCInvite
from django.db import transaction

class Command(BaseCommand):
    help = 'Fix PC member track assignments from PCInvite records'

    def handle(self, *args, **options):
        self.stdout.write('Starting to fix PC member track assignments...')
        
        # Find all accepted PC invites with track information
        accepted_invites = PCInvite.objects.filter(
            status='accepted',
            track__isnull=False
        ).select_related('track', 'conference')
        
        fixed_count = 0
        
        for invite in accepted_invites:
            try:
                # Find the corresponding UserConferenceRole
                user_role = UserConferenceRole.objects.filter(
                    user__email=invite.email,
                    conference=invite.conference,
                    role='pc_member'
                ).first()
                
                if user_role and not user_role.track:
                    # Update the track
                    user_role.track = invite.track
                    user_role.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Fixed track for {invite.name} ({invite.email}) in {invite.conference.name}: {invite.track.name}'
                        )
                    )
                elif user_role and user_role.track:
                    self.stdout.write(
                        self.style.WARNING(
                            f'PC member {invite.name} already has track: {user_role.track.name}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Could not find UserConferenceRole for {invite.name} ({invite.email})'
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing {invite.name}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Fixed {fixed_count} PC member track assignments'
            )
        ) 