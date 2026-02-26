from django.urls import path
from .views import LoginView, ProfileView, ProfileAPIView, LogoutView, SettingsView, UserSettingsAPIView
 
urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('api/profile/', ProfileAPIView.as_view(), name='api-profile'),
    path('api/settings/', UserSettingsAPIView.as_view(), name='api-settings'),
] 
