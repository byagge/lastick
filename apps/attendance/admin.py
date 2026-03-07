from django.contrib import admin
from django.contrib import messages
from .models import AttendanceRecord, AttendanceSettings

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status', 'is_late', 'penalty_amount', 'note']
    list_filter = ['date', 'employee', 'check_out', 'is_late']
    search_fields = ['employee__username', 'employee__first_name', 'employee__last_name', 'note']
    date_hierarchy = 'date'
    ordering = ['-date', '-check_in']
    actions = ['recalculate_penalty']
    
    def status(self, obj):
        if obj.check_out:
            return 'Ушел'
        return 'Присутствует'
    status.short_description = 'Статус'
    
    readonly_fields = ['date', 'check_in', 'is_late', 'penalty_amount']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('employee', 'note')
        }),
        ('Время', {
            'fields': ('check_in', 'check_out')
        }),
        ('Штрафы', {
            'fields': ('is_late', 'penalty_amount'),
            'classes': ('collapse',)
        }),
    )
    
    def recalculate_penalty(self, request, queryset):
        """Принудительно пересчитывает штрафы для выбранных записей"""
        updated_count = 0
        for record in queryset:
            if record.recalculate_penalty():
                updated_count += 1
                record.save()
        
        if updated_count > 0:
            messages.success(request, f'Штрафы пересчитаны для {updated_count} записей')
        else:
            messages.info(request, 'Изменений не требуется')
    
    recalculate_penalty.short_description = 'Пересчитать штрафы'

@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Разрешаем только одну запись
        return not AttendanceSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
