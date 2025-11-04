from django.db import models
from django.db.models import UniqueConstraint

# Create your models here.
class AppUser(models.Model):
    display_name = models.CharField(max_length=120)
    def __str__(self): return self.display_name

class Climb(models.Model):
    # If owner is deleted, keep the climb but anonymize it
    owner = models.ForeignKey(
        AppUser,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_climbs"
    )
    name = models.CharField(max_length=200)
    grade_label = models.CharField(max_length=10)   # e.g., "V3"
    grade_index = models.IntegerField()             # e.g., 3  (V0->0, V1->1, …)
    location = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["grade_index"])]
        constraints = [
            UniqueConstraint(fields=["owner", "name"], name="unique_owner_name")
        ]

    def __str__(self): return f"{self.name} ({self.grade_label})"

class Log(models.Model):
    # If user is deleted, delete their logs
    user = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name="logs"
    )
    climb = models.ForeignKey(
        Climb,
        on_delete=models.RESTRICT,   # keep logs from pointing to missing climbs
        related_name="logs"
    )
    date = models.DateField()
    attempts = models.IntegerField()
    sent = models.BooleanField(default=False)       # did the climber send it?
    note = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["user","date"])]

    def __str__(self):
        who = self.user.display_name if self.user_id else "Unknown"
        return f"{who} - {self.climb} on {self.date}"