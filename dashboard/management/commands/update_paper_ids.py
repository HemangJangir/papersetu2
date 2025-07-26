from django.core.management.base import BaseCommand
from conference.models import Paper
from collections import defaultdict

class Command(BaseCommand):
    help = 'Update all existing papers to use the new paper_id format (ACRONYMYY##) efficiently.'

    def handle(self, *args, **options):
        serials = defaultdict(int)
        to_update = []
        batch_size = 100
        qs = Paper.objects.select_related('conference').order_by('conference', 'submitted_at')
        updated_total = 0
        for paper in qs:
            conf = paper.conference
            acronym = (conf.acronym or 'CONF').upper()
            year = conf.start_date.year if conf.start_date else 0
            yy = str(year)[-2:] if year else 'XX'
            key = (acronym, yy)
            serials[key] += 1
            new_id = f"{acronym}{yy}{serials[key]:02d}"
            if paper.paper_id != new_id:
                paper.paper_id = new_id
                to_update.append(paper)
            if len(to_update) >= batch_size:
                Paper.objects.bulk_update(to_update, ['paper_id'])
                updated_total += len(to_update)
                self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} papers in batch."))
                to_update = []
        if to_update:
            Paper.objects.bulk_update(to_update, ['paper_id'])
            updated_total += len(to_update)
            self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} papers in final batch."))
        self.stdout.write(self.style.SUCCESS(f"Total updated: {updated_total} papers.")) 