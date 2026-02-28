from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeTaskViewSet, tasks_page, EmployeeFullInfoAPIView, employee_info_page, stats_employee_page, employee_orders_page, defects_management_page, employee_dashboard_page, task_detail_page
from .api import (
    EmployeeTaskAssignViewSet, 
    employee_earnings_stats, 
    workshop_earnings_stats, 
    top_earners,
    approve_defect_rework,
    start_defect_rework,
    complete_defect_rework,
    reject_defect,
    defects_list,
    approve_defects_by_order,
    replenish_defects_by_order,
    replenish_defect,
    recalculate_employee_earnings,
)

router = DefaultRouter()
router.register(r'api/employee-tasks', EmployeeTaskViewSet, basename='employee-task')
router.register(r'assign', EmployeeTaskAssignViewSet, basename='assign')

urlpatterns = [
    path('tasks/', tasks_page, name='employee-tasks-page'),
    path('tasks/<int:task_id>/', task_detail_page, name='task-detail-page'),
    path('employee_info/', employee_info_page, name='employee-info-page'),
    path('stats/', stats_employee_page, name='employee-stats-page'),
    path('orders/', employee_orders_page, name='employee-orders-page'),
    path('defects/', defects_management_page, name='defects-management-page'),
    path('dashboard/', employee_dashboard_page, name='employee-dashboard-page'),
    path('api/employee-full-info/<int:pk>/', EmployeeFullInfoAPIView.as_view(), name='employee-full-info-api'),
    
    # API endpoints для статистики заработка
    path('api/earnings/employee/<int:employee_id>/', employee_earnings_stats, name='api_employee_earnings'),
    path('api/earnings/workshop/<int:workshop_id>/', workshop_earnings_stats, name='api_workshop_earnings'),
    path('api/earnings/top/', top_earners, name='api_top_earners'),
    path('api/earnings/recalculate/<int:employee_id>/', recalculate_employee_earnings, name='api_recalculate_earnings'),
    
    # API endpoints для управления браком
    path('api/defects/', defects_list, name='api_defects_list'),
    path('api/defects/approve-by-order/<int:order_id>/', approve_defects_by_order, name='api_approve_defects_by_order'),
    path('api/defects/replenish-by-order/<int:order_id>/', replenish_defects_by_order, name='api_replenish_defects_by_order'),
    path('api/defects/<int:defect_id>/approve/', approve_defect_rework, name='api_approve_defect_rework'),
    path('api/defects/<int:defect_id>/start-rework/', start_defect_rework, name='api_start_defect_rework'),
    path('api/defects/<int:defect_id>/complete-rework/', complete_defect_rework, name='api_complete_defect_rework'),
    path('api/defects/<int:defect_id>/reject/', reject_defect, name='api_reject_defect'),
    path('api/defects/<int:defect_id>/replenish/', replenish_defect, name='api_replenish_defect'),
]
urlpatterns += router.urls 
