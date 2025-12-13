from django.db import models
from django.db.models import UniqueConstraint
from django.core.validators import MinValueValidator, MaxValueValidator
from .validators import InputValidator

# Create your models here.
class AppUser(models.Model):
    display_name = models.CharField(
        max_length=120,
        validators=[InputValidator.safe_name_validator]
    )
    
    class Meta:
        # Index for user lookups and searches
        indexes = [
            models.Index(fields=["display_name"], name="idx_user_display_name"),
        ]
    
    def __str__(self): return self.display_name

class Climb(models.Model):
    # If owner is deleted, keep the climb but anonymize it
    owner = models.ForeignKey(
        AppUser,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_climbs"
    )
    name = models.CharField(
        max_length=200,
        validators=[InputValidator.safe_name_validator]
    )
    grade_label = models.CharField(
        max_length=10,
        validators=[InputValidator.grade_validator]
    )
    grade_index = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(17)]
    )
    location = models.CharField(
        max_length=120, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # indexes:
        # 1. grade_index - for querying climbs by difficulty
        # 2. owner + created_at - for showing user's climbs chronologically
        # 3. grade_index + name - for sorted lists of climbs by difficulty
        # 4. created_at - for recent climbs queries
        indexes = [
            models.Index(fields=["grade_index"], name="idx_climb_grade"),
            models.Index(fields=["owner", "-created_at"], name="idx_climb_owner_date"),
            models.Index(fields=["grade_index", "name"], name="idx_climb_grade_name"),
            models.Index(fields=["-created_at"], name="idx_climb_created"),
        ]
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
        on_delete=models.RESTRICT, # keep logs from pointing to missing climbs
        related_name="logs"
    )
    date = models.DateField()
    attempts = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999)]
    )
    sent = models.BooleanField(default=False)
    note = models.TextField(blank=True)

    class Meta:
        # indexes:
        # 1. user + date - user's logs sorted by date
        # 2. climb + date - for viewing all logs for a specific climb
        # 3. user + sent - for finding user's successful sends
        # 4. climb + sent + user - for counting unique users who sent a climb
        # 5. date - for date-range queries across all users
        indexes = [
            models.Index(fields=["user", "-date"], name="idx_log_user_date"),
            models.Index(fields=["climb", "-date"], name="idx_log_climb_date"),
            models.Index(fields=["user", "sent"], name="idx_log_user_sent"),
            models.Index(fields=["climb", "sent", "user"], name="idx_log_climb_sent_user"),
            models.Index(fields=["-date"], name="idx_log_date"),
        ]

    def __str__(self):
        who = self.user.display_name if self.user_id else "Unknown"
        return f"{who} - {self.climb} on {self.date}"