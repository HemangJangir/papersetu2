from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Fix login for user dinesh8dg (dinesh.goyal@poornima.org)'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='dinesh8dg', email='dinesh.goyal@poornima.org')
            user.is_active = True
            user.is_verified = True
            user.set_password('Manzil@13')
            user.save()
            self.stdout.write(self.style.SUCCESS('User fixed: can now login with email or username and password Manzil@13'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('User not found!')) 