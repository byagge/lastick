from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Страница управления материалами
    path('', views.materials_page, name='materials_page'),
    path('issue/', views.issue_page, name='issue_page'),
    
    # API endpoints
    path('api/materials/', views.api_materials_list, name='api_materials_list'),
    path('api/materials/create/', views.api_material_create, name='api_material_create'),
    path('api/materials/<int:material_id>/update/', views.api_material_update, name='api_material_update'),
    path('api/materials/<int:material_id>/delete/', views.api_material_delete, name='api_material_delete'),
    path('api/materials/bulk-delete/', views.api_materials_bulk_delete, name='api_materials_bulk_delete'),
    path('api/materials/stats/', views.api_materials_stats, name='api_materials_stats'),
    path('api/materials/issue/', views.api_material_issue, name='api_material_issue'),
    path('api/materials/balances/', views.api_material_balances, name='api_material_balances'),
    
    # API для приходов
    path('api/materials/incoming/', views.api_material_incoming, name='api_material_incoming'),
    path('api/materials/<int:material_id>/incomings/', views.api_material_incomings, name='api_material_incomings'),
] 
