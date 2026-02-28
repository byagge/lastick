from django.contrib import admin
from .models import EmployeeTask


@admin.register(EmployeeTask)
class EmployeeTaskAdmin(admin.ModelAdmin):
    list_display = [
        'employee',
        'employee_payment_type',
        'stage',
        'quantity',
        'completed_quantity',
        'defective_quantity',
        'earnings',
        'penalties',
        'net_earnings',
        'created_at',
    ]
    list_filter = [
        'created_at',
        'employee',
        'employee__payment_type',
        'stage__workshop',
        'stage__order__status',
    ]
    search_fields = ['employee__username', 'employee__first_name', 'employee__last_name', 'stage__order__name']
    readonly_fields = ['earnings', 'penalties', 'net_earnings', 'created_at']

    fieldsets = (
        ('Основная информация', {'fields': ('stage', 'employee', 'quantity')}),
        ('Выполнение', {'fields': ('completed_quantity', 'defective_quantity', 'completed_at')}),
        (
            'Финансы',
            {
                'fields': (
                    'earnings',
                    'penalties',
                    'net_earnings',
                ),
                'classes': ('collapse',),
            },
        ),
        (
            'Система',
            {
                'fields': ('created_at',),
                'classes': ('collapse',),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee',
            'stage__workshop',
            'stage__order',
        )

    def employee_payment_type(self, obj):
        return obj.employee.get_payment_type_display()

    employee_payment_type.short_description = 'Тип оплаты'
