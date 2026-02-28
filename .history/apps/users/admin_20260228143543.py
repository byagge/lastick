from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'workshop',
        'payment_type',
        'pay_category',
        'balance',
        'is_active',
    )
    list_filter = (
        'role',
        'workshop',
        'payment_type',
        'pay_category',
        'is_active',
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        (
            'Рабочая информация',
            {
                'fields': (
                    'role',
                    'workshop',
                    'payment_type',
                    'work_schedule',
                    'pay_category',
                )
            },
        ),
        (
            'Финансы',
            {
                'fields': (
                    'balance',
                    'piecework_rate',
                    'fixed_salary',
                )
            },
        ),
        ('Примечания', {'fields': ('notes',)}),
        (
            'Разрешения',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Важные даты', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'username',
                    'password1',
                    'password2',
                    'first_name',
                    'last_name',
                    'email',
                    'phone',
                    'role',
                    'workshop',
                    'payment_type',
                    'work_schedule',
                    'pay_category',
                    'piecework_rate',
                    'fixed_salary',
                ),
            },
        ),
    )

    readonly_fields = ('last_login', 'date_joined', 'created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('workshop')
