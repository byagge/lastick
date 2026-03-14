from rest_framework import serializers
from .models import Product, ProductMaterialNorm
from apps.services.models import Service
from apps.inventory.models import RawMaterial

class ServiceShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ('id', 'name')

class ProductMaterialNormSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    material_unit = serializers.CharField(source='material.unit', read_only=True)
    material_id = serializers.PrimaryKeyRelatedField(queryset=RawMaterial.objects.all(), source='material', write_only=True)

    class Meta:
        model = ProductMaterialNorm
        fields = ['id', 'material_id', 'material_name', 'material_unit', 'amount', 'workshop']
        extra_kwargs = {'workshop': {'required': False}}

class ProductSerializer(serializers.ModelSerializer):
    services = ServiceShortSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), many=True, write_only=True, source='services', required=False
    )
    materials = serializers.SerializerMethodField()
    cost_price = serializers.SerializerMethodField()
    cost_breakdown = serializers.SerializerMethodField()
    average_actual_cost = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    glass_type_display = serializers.CharField(source='get_glass_type_display', read_only=True)
    materials_norms = ProductMaterialNormSerializer(many=True, source='productmaterialnorm_set', required=False)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'type', 'type_display', 'description', 'is_glass', 'glass_type', 'glass_type_display', 'img', 'price',
            'services', 'service_ids', 'materials', 'cost_price',
            'cost_breakdown', 'average_actual_cost',
            'materials_norms',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'services', 'materials', 'cost_price', 'cost_breakdown', 'average_actual_cost', 'type_display', 'glass_type_display']

    def get_materials(self, obj):
        result = []
        for material, amount in obj.get_materials_with_amounts().items():
            result.append({
                'id': material.id,
                'name': material.name,
                'amount': float(amount),
                'unit': material.unit,
                'price': float(material.price),
            })
        return result

    def get_cost_price(self, obj):
        # Decimal -> float для JSON (UI использует числа)
        return float(obj.get_cost_price())

    def get_cost_breakdown(self, obj):
        bd = obj.get_cost_breakdown(quantity=1)
        # Decimal в структуре — сериализуем в float (кроме строковых/прочих)
        def convert(x):
            from decimal import Decimal
            if isinstance(x, Decimal):
                return float(x)
            if isinstance(x, dict):
                return {k: convert(v) for k, v in x.items()}
            if isinstance(x, list):
                return [convert(v) for v in x]
            return x
        return convert(bd)
    
    def get_average_actual_cost(self, obj):
        """Возвращает среднее значение фактической себестоимости на основе всех готовой продукции"""
        avg_cost = obj.get_average_actual_cost()
        if avg_cost is None:
            return None
        return {
            'average_cost_per_unit': float(avg_cost['average_cost_per_unit']),
            'total_quantity': avg_cost['total_quantity'],
            'samples_count': avg_cost['samples_count'],
        }

    def update(self, instance, validated_data):
        # Обновляем основные поля
        services = validated_data.pop('services', None)
        norms_data = validated_data.pop('productmaterialnorm_set', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if services is not None:
            instance.services.set(services)
        instance.save()
        # Обновляем нормы материалов
        if norms_data is not None:
            instance.productmaterialnorm_set.all().delete()
            for row in norms_data:
                ProductMaterialNorm.objects.create(product=instance, **row)
        return instance

    def create(self, validated_data):
        services = validated_data.pop('services', None)
        norms_data = validated_data.pop('productmaterialnorm_set', None)
        product = Product.objects.create(**validated_data)
        if services is not None:
            product.services.set(services)
        if norms_data is not None:
            for row in norms_data:
                ProductMaterialNorm.objects.create(product=product, **row)
        return product 