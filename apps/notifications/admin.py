from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Notification, NotificationType, NotificationTemplate,
    NotificationGroup, NotificationPreference, NotificationLog
)


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    """Административный интерфейс для типов уведомлений"""
    list_display = ['name', 'code', 'icon', 'color', 'is_active']
    list_filter = ['is_active', 'color']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'code', 'description')
        }),
        ('Внешний вид', {
            'fields': ('icon', 'color')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Административный интерфейс для уведомлений"""
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('Статус', {
            'fields': ('is_read', 'created_at')
        }),
    )
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} уведомлений отмечено как прочитанные')
    mark_as_read.short_description = 'Отметить как прочитанные'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Административный интерфейс для шаблонов уведомлений"""
    list_display = [
        'name', 'notification_type', 'is_active', 'created_at', 'updated_at'
    ]
    list_filter = ['is_active', 'notification_type', 'created_at']
    search_fields = ['name', 'title_template', 'message_template']
    ordering = ['name']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'notification_type', 'is_active')
        }),
        ('Шаблоны', {
            'fields': ('title_template', 'message_template'),
            'description': 'Используйте {variable} для подстановки переменных'
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(NotificationGroup)
class NotificationGroupAdmin(admin.ModelAdmin):
    """Административный интерфейс для групп уведомлений"""
    list_display = [
        'name', 'notification_type', 'recipients_count', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'notification_type', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    filter_horizontal = ['recipients']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'notification_type', 'is_active')
        }),
        ('Получатели', {
            'fields': ('recipients',)
        }),
    )
    
    def recipients_count(self, obj):
        """Количество получателей в группе"""
        return obj.recipients.count()
    recipients_count.short_description = 'Получатели'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Административный интерфейс для настроек уведомлений"""
    list_display = [
        'user', 'email_notifications', 'push_notifications', 
        'sms_notifications', 'quiet_hours_display'
    ]
    list_filter = [
        'email_notifications', 'push_notifications', 'sms_notifications',
        'email_daily_digest', 'email_weekly_digest'
    ]
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['user__username']
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Email уведомления', {
            'fields': (
                'email_notifications', 'email_daily_digest', 'email_weekly_digest'
            )
        }),
        ('Push уведомления', {
            'fields': ('push_notifications',)
        }),
        ('SMS уведомления', {
            'fields': ('sms_notifications',)
        }),
        ('Время тишины', {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'description': 'Укажите время, когда не следует отправлять уведомления'
        }),
        ('Настройки по типам', {
            'fields': ('preferences_by_type',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def quiet_hours_display(self, obj):
        """Отображение времени тишины"""
        if obj.quiet_hours_start and obj.quiet_hours_end:
            return f"{obj.quiet_hours_start.strftime('%H:%M')} - {obj.quiet_hours_end.strftime('%H:%M')}"
        return "Не настроено"
    quiet_hours_display.short_description = 'Время тишины'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Административный интерфейс для логов уведомлений"""
    list_display = [
        'notification_title', 'delivery_method', 'delivery_status', 
        'sent_at', 'error_display'
    ]
    list_filter = ['delivery_method', 'delivery_status', 'sent_at']
    search_fields = [
        'notification__title', 'notification__recipient__username'
    ]
    ordering = ['-sent_at']
    readonly_fields = ['sent_at']
    
    fieldsets = (
        ('Уведомление', {
            'fields': ('notification',)
        }),
        ('Доставка', {
            'fields': ('delivery_method', 'delivery_status', 'sent_at')
        }),
        ('Ошибки', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def notification_title(self, obj):
        """Заголовок уведомления с ссылкой"""
        if obj.notification:
            url = reverse(
                'admin:notifications_notification_change', 
                args=[obj.notification.id]
            )
            return format_html('<a href="{}">{}</a>', url, obj.notification.title)
        return '-'
    notification_title.short_description = 'Уведомление'
    
    def error_display(self, obj):
        """Отображение ошибки доставки с форматированием"""
        return mark_safe(f'<div style="white-space:pre-wrap;">{obj.error_message or "-"}</div>')
    error_display.short_description = 'Ошибка'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('notification')

