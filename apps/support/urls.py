from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    # Web Views
    path('', views.support_landing, name='landing'),
    path('dashboard/', views.support_dashboard, name='dashboard'),
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),
    path('create/', views.create_chat, name='create_chat'),
    
    # Admin Views
    path('admin/dashboard/', views.AdminSupportDashboard.as_view(), name='admin_dashboard'),
    path('admin/chat/<int:pk>/', views.AdminChatDetail.as_view(), name='admin_chat_detail'),
    
    # API Views
    path('api/chats/', views.ChatListAPIView.as_view(), name='api_chat_list'),
    path('api/chats/<int:chat_id>/', views.ChatDetailAPIView.as_view(), name='api_chat_detail'),
    path('api/ai/status/', views.AIStatusAPIView.as_view(), name='api_ai_status'),
    
    # Admin API Views
    path('api/admin/ai/toggle/<int:user_id>/', views.AdminToggleAIView.as_view(), name='api_admin_toggle_ai'),
    path('api/admin/chat/<int:chat_id>/message/', views.AdminSendMessageView.as_view(), name='api_admin_send_message'),
] 
