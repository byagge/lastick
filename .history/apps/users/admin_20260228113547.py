from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

# payment_type — это поле в модели User, его нужно добавить в list_display, list_filter, search_fields, fieldsets и add_fieldsets (если уместно).
# количество — вероятно имеется в виду "quantity", но такого поля нет в User. 
# Если это ошибка и имелся в виду "баланс" (balance, отвечает за "количество денег"), то он уже добавлен.
# Если нужно отобразить количество пользователей — это не сюда.
# Поэтому реализуем только payment_type как дополнительное поле
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'workshop', 'balance', 'is_active')
    list_filter = ('role', 'workshop', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Рабочая информация', {'fields': ('role', 'workshop')}),
        ('Финансы', {'fields': ('balance',)}),
        ('Примечания', {'fields': ('notes',)}),
        ('Разрешения', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'role', 'workshop'),
        }),
    )
    
    readonly_fields = ('last_login', 'date_joined', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('workshop')
