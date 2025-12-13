from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import AppUser, Climb, Log
from .validators import InputValidator


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ["id", "display_name"]
    
    def validate_display_name(self, value):
        try:
            sanitized = InputValidator.sanitize_string(value, max_length=120)
            return sanitized
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))


class ClimbSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        source="owner",
        queryset=AppUser.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    total_ascents = serializers.SerializerMethodField()

    def get_total_ascents(self, obj):
        # Uses idx_log_climb_sent_user for efficient counting
        qs = obj.logs.filter(sent=True)
        if obj.owner_id:
            qs = qs.exclude(user_id=obj.owner_id)
        return qs.values("user").distinct().count()

    class Meta:
        model = Climb
        fields = [
            "id",
            "owner",
            "owner_id",
            "name",
            "grade_label",
            "grade_index",
            "location",
            "created_at",
            "total_ascents",
        ]
    
    def validate_name(self, value):
        try:
            sanitized = InputValidator.sanitize_string(value, max_length=200)
            return sanitized
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_location(self, value):
        if value:
            try:
                sanitized = InputValidator.sanitize_string(value, max_length=120)
                return sanitized
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        return value
    
    def validate_grade_index(self, value):
        try:
            return InputValidator.validate_grade_index(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))


class LogSerializer(serializers.ModelSerializer):
    climb_detail = ClimbSerializer(read_only=True, source="climb")

    class Meta:
        model = Log
        fields = ["id", "user", "climb", "climb_detail", "date", "attempts", "sent", "note"]
        read_only_fields = ["user"]
    
    def validate_attempts(self, value):
        try:
            return InputValidator.validate_attempts(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_note(self, value):
        if value:
            try:
                # Allow longer notes but still sanitize
                sanitized = InputValidator.sanitize_string(value, max_length=2000)
                return sanitized
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        return value