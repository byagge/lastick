from django.contrib import admin
from .models import CostingSettings, Product, ProductMaterialNorm, ProductVariant

class ProductMaterialNormInline(admin.TabularInline):
    model = ProductMaterialNorm
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_glass', 'glass_type', 'price', 'cost_price', 'get_services', 'created_at', 'updated_at')
    search_fields = ('name', 'type')
    list_filter = ('type', 'services', 'is_glass', 'glass_type')
    filter_horizontal = ('services',)
    inlines = [ProductMaterialNormInline, ProductVariantInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'type', 'description', 'img', 'price')
        }),
        ('Стеклянные изделия', {
            'fields': ('is_glass', 'glass_type'),
            'classes': ('collapse',),
            'description': 'Настройки для стеклянных изделий'
        }),
        ('Услуги и материалы', {
            'fields': ('services',),
            'description': 'Выберите услуги, необходимые для производства'
        }),
    )

    def get_services(self, obj):
        return ", ".join([s.name for s in obj.services.all()])
    get_services.short_description = 'Услуги'

    def cost_price(self, obj):
        return obj.get_cost_price()
    cost_price.short_description = 'Себестоимость'
    cost_price.admin_order_field = None
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('services')

@admin.register(ProductMaterialNorm)
class ProductMaterialNormAdmin(admin.ModelAdmin):
    list_display = ('product', 'workshop', 'material', 'amount')
    list_filter = ('product', 'workshop', 'material')
    search_fields = ('product__name', 'workshop__name', 'material__name')


@admin.register(CostingSettings)
class CostingSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'overhead_percent',
        'overhead_per_unit',
        'allocate_overhead_from_finance',
        'overhead_period_days',
        'updated_at',
    )
    filter_horizontal = ('overhead_categories',)
