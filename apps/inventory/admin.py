from django.contrib import admin
from .models import RawMaterial, MaterialIncoming, MaterialConsumption


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'quantity', 'unit', 'price', 'total_value', 'min_quantity', 'created_at']
    list_filter = ['unit', 'country', 'created_at']
    search_fields = ['name', 'country', 'description']
    readonly_fields = ['total_value', 'created_at', 'updated_at']
    ordering = ['name']


@admin.register(MaterialIncoming)
class MaterialIncomingAdmin(admin.ModelAdmin):
    list_display = ['material', 'quantity', 'price_per_unit', 'total_value', 'created_at']
    list_filter = ['created_at', 'material']
    search_fields = ['material__name', 'material__country', 'notes']
    readonly_fields = ['total_value', 'created_at']
    ordering = ['-created_at']


@admin.register(MaterialConsumption)
class MaterialConsumptionAdmin(admin.ModelAdmin):
    list_display = ['material', 'quantity', 'workshop', 'order', 'consumed_at']
    list_filter = ['consumed_at', 'workshop', 'material']
    search_fields = ['material__name', 'workshop__name', 'order__name']
    readonly_fields = ['consumed_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('material', 'quantity', 'workshop', 'order')
        }),
        ('Система', {
            'fields': ('employee_task', 'consumed_at'),
            'classes': ('collapse',)
        }),
    )