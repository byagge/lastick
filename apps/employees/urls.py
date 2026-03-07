from django.urls import path
from .views import employees_list
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet
from .views import employees_by_workshop, add_employee_to_workshop, employees_workshop_list
from .views import all_workshops, all_employees_by_workshop
from .views import my_workshops, impersonate_user, release_impersonation, change_employee_password

router = DefaultRouter()
router.register(r'api/employees', EmployeeViewSet, basename='employee')

urlpatterns = [
    path('', employees_workshop_list, name='employees_list'),
    path('api/employees/by_workshop/', employees_by_workshop, name='employees_by_workshop'),
    path('api/employees/add_to_workshop/', add_employee_to_workshop, name='add_employee_to_workshop'),
    path('api/all_workshops/', all_workshops, name='all_workshops'),
    path('api/employees/all_by_workshop/', all_employees_by_workshop, name='all_employees_by_workshop'),
    path('api/my_workshops/', my_workshops, name='my_workshops'),
    path('impersonate/<int:user_id>/', impersonate_user, name='impersonate_user'),
    path('impersonate/release/', release_impersonation, name='release_impersonation'),
    path('api/employees/<int:employee_id>/change_password/', change_employee_password, name='change_employee_password'),
]

urlpatterns += router.urls 