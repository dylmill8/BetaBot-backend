from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Max
from .models import AppUser, Climb, Log
from .serializers import ClimbSerializer, LogSerializer

# Create your views here.
DEMO_USER_ID = 1  # single-user for Stage 2 demo

class ClimbViewSet(viewsets.ModelViewSet):
    queryset = Climb.objects.select_related("owner").all().order_by("grade_index", "name")
    serializer_class = ClimbSerializer

    def get_queryset(self):
        # Keep climbs even if owner is deleted (owner may be NULL)
        return Climb.objects.select_related("owner").all().order_by("grade_index", "name")

    def perform_create(self, serializer):
        # Default new climbs to the demo owner for now
        owner = AppUser.objects.filter(pk=DEMO_USER_ID).first()
        serializer.save(owner=owner)

class LogViewSet(viewsets.ModelViewSet):
    queryset = Log.objects.select_related("climb", "user").all()
    serializer_class = LogSerializer

    def get_queryset(self):
        qs = Log.objects.select_related("climb","user").filter(user_id=DEMO_USER_ID)

        # grade range filters
        min_g = self.request.query_params.get("min_grade")
        max_g = self.request.query_params.get("max_grade")
        if min_g is not None:
            qs = qs.filter(climb__grade_index__gte=int(min_g))
        if max_g is not None:
            qs = qs.filter(climb__grade_index__lte=int(max_g))
        
        # sort by date
        sort = self.request.query_params.get("sort")
        qs = qs.order_by("date", "id") if sort == "asc" else qs.order_by("-date", "-id")
        return qs

    def perform_create(self, serializer):
        # Auto-assign demo user unless client sends user explicitly
        serializer.save(user_id=DEMO_USER_ID)

    @action(detail=False, methods=["get"])
    def report(self, request):
        qs = self.get_queryset()
        data = {
            "count": qs.count(),
            "avg_attempts": qs.aggregate(Avg("attempts"))["attempts__avg"],
            "best_grade_index": qs.aggregate(Max("climb__grade_index"))["climb__grade_index__max"],
            "by_grade": list(
                qs.values("climb__grade_label").annotate(n=Count("id")).order_by("climb__grade_label")
            ),
            "sample": LogSerializer(qs[:50], many=True).data
        }
        return Response(data)