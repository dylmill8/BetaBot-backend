from django.core.management.base import BaseCommand
from core.models import AppUser, Climb

CLIMBS = [
  ("Moon Arete",     "V3", 3, "Kilter Board"),
  ("Crimp Ladder",   "V2", 2, "Kilter Board"),
  ("Dyno Alley",     "V4", 4, "Kilter Board"),
  ("Volume Traverse","V1", 1, "Kilter Board"),
  ("Small Edges",    "V5", 5, "Kilter Board"),
]

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        owner, _ = AppUser.objects.get_or_create(
            id=1, defaults={"display_name": "Dylan"}
        )
        for name, glabel, gindex, loc in CLIMBS:
            Climb.objects.get_or_create(
                name=name, grade_label=glabel, grade_index=gindex, location=loc,
                defaults={"owner": owner}
            )
        self.stdout.write(self.style.SUCCESS("Seeded demo user and climbs."))