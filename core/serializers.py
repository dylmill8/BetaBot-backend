from rest_framework import serializers
from .models import AppUser, Climb, Log


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ["id", "display_name"]


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


class LogSerializer(serializers.ModelSerializer):
    climb_detail = ClimbSerializer(read_only=True, source="climb")

    class Meta:
        model = Log
        fields = ["id", "user", "climb", "climb_detail", "date", "attempts", "sent", "note"]
        read_only_fields = ["user"]