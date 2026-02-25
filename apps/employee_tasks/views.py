from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import EmployeeTask
from .serializers import EmployeeTaskSerializer
from apps.employees.serializers import EmployeeSerializer
from apps.users.models import User


class EmployeeTaskViewSet(viewsets.ModelViewSet):
    queryset = EmployeeTask.objects.select_related(
        'stage__order_item__product',
        'stage__workshop',
        'stage__order',
        'stage__order__client',
        'employee',
    ).prefetch_related(
        'stage__order_item__product__services',
        'stage__order__items__product',
    ).all().order_by('-created_at')
    serializer_class = EmployeeTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'stage__operation',
        'stage__order_item__product__name',
        'employee__first_name',
        'employee__last_name',
        'stage__order__name',
    ]
    ordering_fields = ['created_at', 'completed_quantity', 'quantity']

    def get_queryset(self):
        queryset = super().get_queryset()
        employee_id = self.request.query_params.get('employee')
        order_id = self.request.query_params.get('order')
        stage_id = self.request.query_params.get('stage')

        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if order_id:
            queryset = queryset.filter(stage__order_id=order_id)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)

        return queryset

    def update(self, request, *args, **kwargs):
        """Allow update and keep default behavior."""
        return super().update(request, *args, **kwargs)


class EmployeeFullInfoAPIView(APIView):
    def get(self, request, pk):
        try:
            employee = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)

        employee_data = EmployeeSerializer(employee).data
        tasks = EmployeeTask.objects.filter(employee=employee)
        employee_data['tasks'] = EmployeeTaskSerializer(tasks, many=True).data
        return Response(employee_data)


def tasks_page(request):
    return render(request, 'tasks.html')


def employee_info_page(request):
    return render(request, 'employee_info.html')


def stats_employee_page(request):
    return render(request, 'stats_employee.html')


def employee_orders_page(request):
    return render(request, 'employee_orders.html')


def defects_management_page(request):
    """Render defects management page."""
    return render(request, 'defects_management.html')


def task_detail_page(request, task_id):
    """Render task detail page."""
    return render(request, 'task_detail.html', {
        'task_id': task_id,
    })
