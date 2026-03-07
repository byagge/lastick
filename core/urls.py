"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app import views
    2. Add a URL to urlpatterns:  path('', other_app.views.Home, name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from .views import HomeView
from .error_views import (
    custom_400, custom_401, custom_403, custom_404, 
    custom_500, custom_502, custom_503, custom_error
)
from .test_error_views import (
    test_400_view, test_401_view, test_403_view, test_404_view,
    test_500_view, test_502_view, test_503_view, test_custom_error_view,
    test_trigger_500, test_trigger_403, test_trigger_400
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
	path('', HomeView.as_view(), name='home'),  # Корневой URL с проверкой ролей
    path('banned/', TemplateView.as_view(template_name='banned.html'), name='banned'),
	path('accounts/', include('users.urls')),
	path('settings/', RedirectView.as_view(url='/accounts/profile/', permanent=False), name='settings'),  # Редирект на профиль
	path('clients/', include('clients.urls')),  # Изменяем с '' на 'clients/'
	path('workshops/', include('apps.operations.workshops.urls')),
	path('dashboard/', include('apps.odashboard.urls')),
	path('employees/', include('apps.employees.urls')),
	path('inventory/', include('apps.inventory.urls')),
	path('services/', include('apps.services.urls')),
	path('products/', include('apps.products.urls')),
	path('defects/', include('apps.defects.urls')),
	path('orders/', include('apps.orders.urls')),
	path('finished_goods/', include('apps.finished_goods.urls')),
	path('attendance/', include('apps.attendance.urls')),
	path('employee_tasks/', include('apps.employee_tasks.urls')),
	path('finance/', include('apps.finance.urls')),
	path('director/', include('apps.director.urls')),
	path('api/workshops/', include('apps.workshops.urls')),  # Прямой маршрут для API
	path('admin/', admin.site.urls),
	path('stats/', TemplateView.as_view(template_name='stats_master.html'), name='stats-master'),
	path('notifications/', include('apps.notifications.urls', namespace='notifications')),
	path('menu/', TemplateView.as_view(template_name='mobile/menu.html'), name='mobile-menu'),
	path('error/', custom_error, name='custom_error'),
	path('support/', include('apps.support.urls')),
	path('online/', include('apps.online.urls')),
	# Тестовые URL для проверки страниц ошибок (только для разработки)
	path('test/error/400/', test_400_view, name='test_400'),
	path('test/error/401/', test_401_view, name='test_401'),
	path('test/error/403/', test_403_view, name='test_403'),
	path('test/error/404/', test_404_view, name='test_404'),
	path('test/error/500/', test_500_view, name='test_500'),
	path('test/error/502/', test_502_view, name='test_502'),
	path('test/error/503/', test_503_view, name='test_503'),
	path('test/error/custom/', test_custom_error_view, name='test_custom_error'),
	path('test/error/trigger/500/', test_trigger_500, name='test_trigger_500'),
	path('test/error/trigger/403/', test_trigger_403, name='test_trigger_403'),
	path('test/error/trigger/400/', test_trigger_400, name='test_trigger_400'),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Обработчики ошибок
handler400 = 'core.error_views.custom_400'
handler401 = 'core.error_views.custom_401'
handler403 = 'core.error_views.custom_403'
handler404 = 'core.error_views.custom_404'
handler500 = 'core.error_views.custom_500'
handler502 = 'core.error_views.custom_502'
handler503 = 'core.error_views.custom_503'

