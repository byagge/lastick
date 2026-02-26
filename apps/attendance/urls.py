from django.urls import path
from .views import (
    checkin_by_qr, qr_scanner_page, checkout_employee, attendance_overview, 
    attendance_list, attendance_page, recalculate_today_penalties,
    employee_attendance_status, auto_checkout_after_6pm, employee_status_by_workshop,
    update_attendance_penalty
)

urlpatterns = [
    path('', attendance_page, name='attendance_main'),
    path('api/checkin/', checkin_by_qr, name='attendance_checkin'),
    path('api/checkout/', checkout_employee, name='attendance_checkout'),
    path('api/overview/', attendance_overview, name='attendance_overview'),
    path('api/list/', attendance_list, name='attendance_list'),
    path('api/penalty/', update_attendance_penalty, name='attendance_penalty_update'),
    path('api/recalculate-penalties/', recalculate_today_penalties, name='recalculate_penalties'),
    path('api/employee-status/', employee_attendance_status, name='employee_attendance_status'),
    path('api/auto-checkout/', auto_checkout_after_6pm, name='auto_checkout_after_6pm'),
    path('api/employee-status-by-workshop/', employee_status_by_workshop, name='employee_status_by_workshop'),
    path('scan/', qr_scanner_page, name='attendance_qr_scanner'),
] 
