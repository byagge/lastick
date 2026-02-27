from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet,
    OrderPageView,
    OrderCreateAPIView,
    OrderStageConfirmAPIView,
    StageViewSet,
    OrderStageTransferAPIView,
    OrderStagePostponeAPIView,
    OrderStageNoTransferAPIView,
    DashboardOverviewAPIView,
    DashboardRevenueChartAPIView,
    PlansMasterView,
    PlansMasterDetailView,
    RequestsEntryView,
    AdminRequestsView,
    AdminClientRequestsView,
    ApproveRequestAPIView,
    ExportRequestsExcelView,
    ExportRequestsExcelForClientView,
)
from .api import WorkshopStagesView, StageDetailView
from django.urls import path, include
from django.views.generic import TemplateView

app_name = 'orders'

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'stages', StageViewSet, basename='stage')

urlpatterns = [
    # Главная страница orders — интерфейс создания заявок (desktop/mobile)
    path('', RequestsEntryView.as_view(), name='orders-home'),
    
    # Админ заявок
    path('admin/', AdminRequestsView.as_view(), name='admin-requests'),
    path('admin/client/<int:client_id>/', AdminClientRequestsView.as_view(), name='admin-client-requests'),
    
    # API для одобрения заявок
    path('api/requests/approve/<int:request_id>/', ApproveRequestAPIView.as_view(), name='approve-request'),
    path('api/', include(router.urls)),
    path('api/create/', OrderCreateAPIView.as_view(), name='orders-create'),
    path('api/stages/<int:stage_id>/confirm/', OrderStageConfirmAPIView.as_view(), name='order-stage-confirm'),
    path('api/stages/<int:stage_id>/transfer/', OrderStageTransferAPIView.as_view(), name='order-stage-transfer'),
    path('api/stages/<int:stage_id>/postpone/', OrderStagePostponeAPIView.as_view(), name='order-stage-postpone'),
    path('api/stages/<int:stage_id>/no-transfer/', OrderStageNoTransferAPIView.as_view(), name='order-stage-no-transfer'),
    path('api/dashboard/overview/', DashboardOverviewAPIView.as_view(), name='orders-dashboard-overview'),
    path('api/dashboard/revenue-chart/', DashboardRevenueChartAPIView.as_view(), name='orders-dashboard-revenue-chart'),
    path('api/workshop-stages/', WorkshopStagesView.as_view(), name='orders-workshop-stages'),
    path('export/excel/', ExportRequestsExcelView.as_view(), name='export_requests_excel'),
    path('export/excel/client/<int:client_id>/', ExportRequestsExcelForClientView.as_view(), name='export_requests_excel_for_client'),
] 