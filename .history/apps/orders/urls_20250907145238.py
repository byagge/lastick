from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderPageView, OrderCreateAPIView, OrderStageConfirmAPIView, StageViewSet, OrderStageTransferAPIView, OrderStagePostponeAPIView, OrderStageNoTransferAPIView, DashboardOverviewAPIView, DashboardRevenueChartAPIView, PlansMasterView, PlansMasterDetailView
from .api import WorkshopStagesView, StageDetailView
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from .views import AdminRequestsView, AdminClientRequestsView, ApproveRequestAPIView, ExportRequestsExcelView, ExportRequestsExcelForClientView

app_name = 'orders'

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'stages', StageViewSet, basename='stage')

urlpatterns = [
    # Редирект с главной страницы orders на админ заявок
    path('', RedirectView.as_view(url='/orders/admin/', permanent=False), name='orders-home'),
    
    # Админ заявок
    path('admin/', AdminRequestsView.as_view(), name='admin-requests'),
    path('admin/client/<int:client_id>/', AdminClientRequestsView.as_view(), name='admin-client-requests'),
    
    # Страницы планов мастера
    path('plans/master/', PlansMasterView.as_view(), name='plans-master'),
    path('plans/master/<int:stage_id>/', PlansMasterDetailView.as_view(), name='plans-master-detail'),
    
    # API для планов мастера и этапов
    path('api/stages/', WorkshopStagesView.as_view(), name='api-stages-list'),
    path('api/stages/<int:stage_id>/', StageDetailView.as_view(), name='api-stages-detail'),
    path('api/stages/<int:stage_id>/confirm/', OrderStageConfirmAPIView.as_view(), name='api-stages-confirm'),
    path('api/stages/<int:stage_id>/transfer/', OrderStageTransferAPIView.as_view(), name='api-stages-transfer'),
    path('api/stages/<int:stage_id>/no-transfer/', OrderStageNoTransferAPIView.as_view(), name='api-stages-no-transfer'),
    
    # API для одобрения заявок
    path('api/requests/approve/<int:request_id>/', ApproveRequestAPIView.as_view(), name='approve-request'),
    path('export/excel/', ExportRequestsExcelView.as_view(), name='export_requests_excel'),
    path('export/excel/client/<int:client_id>/', ExportRequestsExcelForClientView.as_view(), name='export_requests_excel_for_client'),
] 