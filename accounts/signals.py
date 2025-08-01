from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import User

@receiver(pre_save, sender=User)
def cleanup_old_unverified_users(sender, instance, **kwargs):
    """
    Clean up unverified users older than 7 days when any user is saved.
    This helps keep the database clean automatically.
    """
    # Only run this occasionally to avoid performance issues
    # We'll use a simple check based on the current time
    current_minute = timezone.now().minute
    
    # Only run cleanup every 10 minutes (when minute ends with 0)
    if current_minute % 10 == 0:
        cutoff_date = timezone.now() - timedelta(days=7)
        
        # Delete unverified users older than 7 days
        old_unverified_users = User.objects.filter(
            is_verified=False,
            date_joined__lt=cutoff_date
        )
        
        if old_unverified_users.exists():
            count = old_unverified_users.count()
            old_unverified_users.delete()
            print(f"Cleaned up {count} old unverified users") 