from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Max
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import AppUser, Climb, Log
from .serializers import ClimbSerializer, LogSerializer
from .validators import InputValidator

# Create your views here.
DEMO_USER_ID = 1  # single-user for Stage 2 & 3 demo

class ClimbViewSet(viewsets.ModelViewSet):
    queryset = Climb.objects.select_related("owner").all().order_by("grade_index", "name")
    serializer_class = ClimbSerializer

    def get_queryset(self):
        qs = Climb.objects.select_related("owner").all()
        
        try:
            # Validate and sanitize query parameters
            params = self.request.query_params.dict()
            sanitized = InputValidator.validate_query_params(params)
            
            # Grade range filters
            if 'min_grade' in sanitized:
                qs = qs.filter(grade_index__gte=sanitized['min_grade'])
            if 'max_grade' in sanitized:
                qs = qs.filter(grade_index__lte=sanitized['max_grade'])
            
            # Sorting
            if sanitized.get('sort') == 'desc':
                qs = qs.order_by('-grade_index', 'name')
            else:
                qs = qs.order_by('grade_index', 'name')
                
        except ValidationError:
            # On validation error, return default ordering
            qs = qs.order_by('grade_index', 'name')
        
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        # Default new climbs to the demo owner for now
        owner = AppUser.objects.filter(pk=DEMO_USER_ID).first()
        serializer.save(owner=owner)
    
    @transaction.atomic
    def perform_update(self, serializer):
        serializer.save()
    
    @transaction.atomic
    def perform_destroy(self, instance):
        instance.delete()

class LogViewSet(viewsets.ModelViewSet):
    queryset = Log.objects.select_related("climb", "user").all()
    serializer_class = LogSerializer

    def get_queryset(self):
        qs = Log.objects.select_related("climb","user").filter(user_id=DEMO_USER_ID)

        try:
            # Validate and sanitize query parameters to prevent injection
            params = self.request.query_params.dict()
            sanitized = InputValidator.validate_query_params(params)
            
            # grade range filters using idx_log_climb_date
            if 'min_grade' in sanitized:
                qs = qs.filter(climb__grade_index__gte=sanitized['min_grade'])
            if 'max_grade' in sanitized:
                qs = qs.filter(climb__grade_index__lte=sanitized['max_grade'])
            
            # date range filters - uses idx_log_user_date or idx_log_date index
            if 'start_date' in sanitized:
                qs = qs.filter(date__gte=sanitized['start_date'])
            if 'end_date' in sanitized:
                qs = qs.filter(date__lte=sanitized['end_date'])
            
            # sort by date - uses idx_log_user_date index
            sort_order = sanitized.get('sort', 'desc')
            qs = qs.order_by("date", "id") if sort_order == "asc" else qs.order_by("-date", "-id")
            
        except ValidationError as e:
            # Return empty queryset if validation fails
            # Error will be caught by DRF exception handler
            raise
        
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        # Auto-assign demo user unless client sends user explicitly
        serializer.save(user_id=DEMO_USER_ID)
    
    @transaction.atomic
    def perform_update(self, serializer):
        serializer.save()
    
    @transaction.atomic
    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=["get"])
    def report(self, request):
        with transaction.atomic(durable=True):
            # isolation level is REPEATABLE READ for consistent reporting
            # this prevents non-repeatable reads where the same query could return
            # different results if executed multiple times in the transaction
            from django.db import connection
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            
            qs = self.get_queryset()

            data = {
                "count": qs.count(),
                "avg_attempts": qs.aggregate(Avg("attempts"))["attempts__avg"],
                "best_grade_index": qs.aggregate(Max("climb__grade_index"))["climb__grade_index__max"],
                "by_grade": list(
                    qs.filter(sent=True).values("climb__grade_label").annotate(n=Count("id")).order_by("climb__grade_label")
                ),
                "sample": LogSerializer(qs[:50], many=True).data
            }
            
        return Response(data)
    
    @action(detail=False, methods=["post"])
    @transaction.atomic
    def bulk_create(self, request):
        logs_data = request.data.get('logs', [])
        
        if not logs_data or not isinstance(logs_data, list):
            return Response(
                {"error": "logs field must be a non-empty array"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_logs = []
        for log_data in logs_data:
            # Validate each log entry
            serializer = LogSerializer(data=log_data)
            serializer.is_valid(raise_exception=True)
            created_logs.append(serializer.save(user_id=DEMO_USER_ID))
        
        return Response(
            LogSerializer(created_logs, many=True).data,
            status=status.HTTP_201_CREATED
        )