from django.core.management.base import BaseCommand
from conference.models import Conference, ConferenceFeatureToggle, FEATURE_CHOICES

class Command(BaseCommand):
    help = 'Seed ConferenceFeatureToggle entries for all features for all conferences.'

    def handle(self, *args, **options):
        count = 0
        for conf in Conference.objects.all():
            for feature, _ in FEATURE_CHOICES:
                obj, created = ConferenceFeatureToggle.objects.get_or_create(
                    conference=conf, feature=feature, defaults={'enabled': True}
                )
                if created:
                    count += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {count} feature toggles.')) 