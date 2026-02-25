from django.contrib import admin
from apps.users.models import User
from .models import (
    EmployeeStatistics,
    EmployeeTask,
    EmployeeNotification,
    EmployeeContactInfo,
    EmployeeMedicalInfo
)


class EmployeeContactInfoInline(admin.TabularInline):
    model = EmployeeContactInfo
    extra = 0
    fields = ['emergency_contact', 'emergency_phone', 'address', 'alternative_phone', 'skype', 'telegram']
    can_delete = True


class EmployeeMedicalInfoInline(admin.TabularInline):
    model = EmployeeMedicalInfo
    extra = 0
    fields = ['blood_type', 'allergies', 'chronic_diseases', 'medications', 'medical_examination_date', 'medical_book_number']
    can_delete = True


class EmployeeStatisticsInline(admin.TabularInline):
    model = EmployeeStatistics
    extra = 0
    fields = [
        'completed_works', 'defects', 'monthly_salary', 'efficiency',
        'avg_productivity', 'defect_rate', 'hours_worked', 'overtime_hours',
        'quality_score', 'deadline_compliance', 'initiative_score', 'teamwork_score'
    ]
    readonly_fields = ['productivity_chart', 'monthly_productivity', 'salary_history', 'last_updated']
    can_delete = True


class EmployeeTaskInline(admin.TabularInline):
    model = EmployeeTask
    extra = 1
    fields = ['text', 'completed', 'created_at']
    readonly_fields = ['created_at']


class EmployeeNotificationInline(admin.TabularInline):
    model = EmployeeNotification
    extra = 1
    fields = ['title', 'text', 'is_read', 'created_at']
    readonly_fields = ['created_at']


# Register employee-specific models
@admin.register(EmployeeStatistics)
class EmployeeStatisticsAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'completed_works', 'defects', 'monthly_salary', 
        'efficiency', 'quality_score'
    ]
    list_filter = [
        'efficiency', 'quality_score', 'deadline_compliance',
        ('employee__workshop', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['productivity_chart', 'monthly_productivity', 'salary_history', 'last_updated']
    
    fieldsets = (
        ('Сотрудник', {
            'fields': ('employee',)
        }),
        ('Основные показатели', {
            'fields': (
                'completed_works', 'defects', 'monthly_salary', 'efficiency'
            )
        }),
        ('Дополнительные метрики', {
            'fields': (
                'avg_productivity', 'defect_rate', 'hours_worked', 'overtime_hours'
            ),
            'classes': ('collapse',)
        }),
        ('Качество работы', {
            'fields': (
                'quality_score', 'deadline_compliance', 'initiative_score', 'teamwork_score'
            ),
            'classes': ('collapse',)
        }),
        ('Графики и история', {
            'fields': ('productivity_chart', 'monthly_productivity', 'salary_history'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmployeeTask)
class EmployeeTaskAdmin(admin.ModelAdmin):
    list_display = ['employee', 'text', 'completed', 'created_at']
    list_filter = ['completed', 'created_at', ('employee__workshop', admin.RelatedOnlyFieldListFilter)]
    search_fields = ['employee__first_name', 'employee__last_name', 'text']
    readonly_fields = ['created_at']
    list_editable = ['completed']


@admin.register(EmployeeNotification)
class EmployeeNotificationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at', ('employee__workshop', admin.RelatedOnlyFieldListFilter)]
    search_fields = ['employee__first_name', 'employee__last_name', 'title', 'text']
    readonly_fields = ['created_at']
    list_editable = ['is_read']


@admin.register(EmployeeContactInfo)
class EmployeeContactInfoAdmin(admin.ModelAdmin):
    list_display = ['employee', 'emergency_contact', 'emergency_phone', 'alternative_phone']
    search_fields = ['employee__first_name', 'employee__last_name', 'emergency_contact', 'emergency_phone']
    list_filter = [('employee__workshop', admin.RelatedOnlyFieldListFilter)]
    
    fieldsets = (
        ('Сотрудник', {
            'fields': ('employee',)
        }),
        ('Экстренная связь', {
            'fields': ('emergency_contact', 'emergency_phone')
        }),
        ('Адрес', {
            'fields': ('address',)
        }),
        ('Дополнительные контакты', {
            'fields': ('alternative_phone', 'skype', 'telegram')
        }),
    )


@admin.register(EmployeeMedicalInfo)
class EmployeeMedicalInfoAdmin(admin.ModelAdmin):
    list_display = ['employee', 'blood_type', 'medical_examination_date', 'medical_book_number']
    search_fields = ['employee__first_name', 'employee__last_name']
    list_filter = ['blood_type', 'medical_examination_date', ('employee__workshop', admin.RelatedOnlyFieldListFilter)]
    
    fieldsets = (
        ('Сотрудник', {
            'fields': ('employee',)
        }),
        ('Медицинская информация', {
            'fields': ('blood_type', 'allergies', 'chronic_diseases', 'medications')
        }),
        ('Медосмотры', {
            'fields': ('medical_examination_date', 'medical_examination_expiry')
        }),
        ('Медицинская книжка', {
            'fields': ('medical_book_number', 'medical_book_issue_date', 'medical_book_expiry_date')
        }),
    )


# Function to enhance the existing User admin with employee-specific inlines
def enhance_user_admin():
    """Add employee-specific inlines to the existing User admin"""
    from apps.users.admin import UserAdmin
    
    # Add employee-specific inlines to the existing UserAdmin
    if not hasattr(UserAdmin, '_employee_inlines_added'):
        UserAdmin.inlines = list(getattr(UserAdmin, 'inlines', [])) + [
            EmployeeContactInfoInline,
            EmployeeMedicalInfoInline,
            EmployeeStatisticsInline,
            EmployeeTaskInline,
            EmployeeNotificationInline,
        ]
        UserAdmin._employee_inlines_added = True


# Call the enhancement function when the admin module is loaded
enhance_user_admin()
