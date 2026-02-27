from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'api/workshops', views.WorkshopViewSet, basename='workshop')

urlpatterns = [
    path('', views.workshops_list, name='workshops'),
    path('mobile/', views.workshops_mobile_page, name='workshops-mobile'),
    path('master/', views.master_dashboard, name='master-dashboard'),
    path('api/workshops/<int:workshop_id>/orders/', views.workshop_orders_info, name='workshop-orders-info'),
    path('api/workshops/orders/', views.all_workshops_orders_info, name='all-workshops-orders-info'),
    path('api/workshops/stats/', views.workshops_stats, name='workshops-stats'),
    # Добавляем недостающие API endpoints
    path('api/masters/', views.workshop_masters, name='workshop-masters'),
    path('api/employees/', views.workshop_employees, name='workshop-employees'),
    path('api/add-master/', views.add_workshop_master, name='add-workshop-master'),
    path('api/remove-master/', views.remove_workshop_master, name='remove-workshop-master'),
    path('api/workshops/master-stats/', views.master_workshops_stats, name='master-workshops-stats'),
]

urlpatterns += router.urls 
