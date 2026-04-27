from rest_framework import serializers
from .models import Order, OrderStage, OrderDefect, OrderItem, create_order_stages
from apps.clients.models import Client
from apps.products.models import Product
from apps.operations.workshops.models import Workshop
from apps.employee_tasks.serializers import EmployeeTaskSerializer


def _safe_str(value):
    """Converts bytes to utf-8 string safely; leaves other types unchanged."""
    try:
        if isinstance(value, (bytes, bytearray)):
            return value.decode('utf-8', errors='ignore')
        return value
    except Exception:
        return ''


class ClientFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'company', 'phone', 'email', 'address', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in ['name', 'company', 'phone', 'email', 'address']:
            if key in data:
                data[key] = _safe_str(data.get(key))
        return data


class ProductFullSerializer(serializers.ModelSerializer):
    glass_type_display = serializers.CharField(source='get_glass_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'type', 'description', 'is_glass', 'glass_type', 'glass_type_display', 'img', 'price', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in ['name', 'type', 'description']:
            if key in data:
                data[key] = _safe_str(data.get(key))
        # Normalize img to URL string if possible
        try:
            img = getattr(instance, 'img', None)
            if img:
                data['img'] = getattr(img, 'url', None) or _safe_str(str(img))
        except Exception:
            pass
        return data


class WorkshopFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in ['name', 'description']:
            if key in data:
                data[key] = _safe_str(data.get(key))
        return data


class WorkshopShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = ['id', 'name']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductFullSerializer(read_only=True, allow_null=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product', required=False, allow_null=True)
    glass_type_display = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_id', 'quantity', 'size', 'color',
            'glass_type', 'glass_type_display', 'paint_type', 'paint_color',
            'cnc_specs', 'cutting_specs', 'preparation_specs', 'packaging_notes',
            'glass_cutting_completed', 'glass_cutting_quantity', 'packaging_received_quantity',
            'order', 'display_name'
        ]
    
    def get_glass_type_display(self, obj):
        """Безопасно возвращает отображение типа стекла"""
        try:
            return obj.get_glass_type_display()
        except:
            return obj.glass_type or ""
    
    def get_order(self, obj):
        # Минимальная информация о заказе для отображения в шаблонах
        if not obj.order:
            return None
        try:
            client = obj.order.client
            # Получаем workshop_id из контекста для фильтрации
            workshop_id = self.context.get('workshop_id', 0)
            
            # Получаем все товары заказа без рекурсивной сериализации
            items = []
            if obj.order.items.exists():
                for item in obj.order.items.all():
                    # Фильтруем стеклянные товары для цехов после ID5
                    if workshop_id > 5 and item.product and getattr(item.product, 'is_glass', False):
                        continue
                        
                    items.append({
                        'id': item.id,
                        'quantity': item.quantity,
                        'size': item.size,
                        'color': item.color,
                        'display_name': item.get_display_name(),
                        'product': {
                            'id': item.product.id if item.product else None,
                            'name': item.product.name if item.product else 'Не указан',
                            'is_glass': item.product.is_glass if item.product else False
                        } if item.product else None
                    })
            return {
                'id': obj.order.id,
                'name': obj.order.name,
                'created_at': obj.order.created_at,
                'status_display': obj.order.status_display,
                'comment': obj.order.comment,
                'client': {'id': client.id, 'name': client.name} if client else None,
                'items': items
            }
        except Exception:
            # В случае ошибки возвращаем минимальную информацию
            return {
                'id': obj.order.id if obj.order else None,
                'name': obj.order.name if obj.order else 'Не указано',
                'created_at': obj.order.created_at if obj.order else None,
                'status_display': 'Не указан',
                'comment': '',
                'client': None,
                'items': []
            }

    def get_display_name(self, obj):
        try:
            return obj.get_display_name()
        except Exception:
            return obj.product.name if obj.product else 'Товар'

    def to_representation(self, instance):
        """Переопределяем для безопасной обработки null значений"""
        data = super().to_representation(instance)
        # Sanitize potentially byte-valued fields
        for key in ['size', 'color', 'glass_type', 'paint_type', 'paint_color', 'cnc_specs', 'cutting_specs', 'preparation_specs', 'packaging_notes']:
            if key in data:
                data[key] = _safe_str(data.get(key))
        # Sanitize nested product name if present
        if isinstance(data.get('product'), dict) and 'name' in data['product']:
            data['product']['name'] = _safe_str(data['product']['name'])
        # Sanitize minimal order info if present
        if isinstance(data.get('order'), dict):
            if 'name' in data['order']:
                data['order']['name'] = _safe_str(data['order']['name'])
            if 'comment' in data['order']:
                data['order']['comment'] = _safe_str(data['order']['comment'])
        return data


class OrderStageSerializer(serializers.ModelSerializer):
    workshop = WorkshopShortSerializer(read_only=True)
    assigned = EmployeeTaskSerializer(source='employee_tasks', many=True, read_only=True)
    order_name = serializers.CharField(source='order.name', read_only=True)
    order_item = OrderItemSerializer(read_only=True, allow_null=True)
    done_count = serializers.IntegerField(read_only=True)
    defective_count = serializers.IntegerField(read_only=True)
    workshop_info = serializers.SerializerMethodField()
    aggregated_items = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderStage
        fields = [
            'id', 'workshop', 'order_name', 'order_item', 'operation', 'sequence', 
            'parallel_group', 'plan_quantity', 'completed_quantity', 'done_count', 
            'defective_count', 'deadline', 'status', 'in_progress', 'defective', 
            'completed', 'date', 'comment', 'assigned', 'workshop_info',
            'aggregated_items', 'products', 'total_quantity'
        ]
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        try:
            return obj.get_workshop_info()
        except:
            return {}
    
    def get_aggregated_items(self, obj):
        """Если этап агрегированный (order_item is None), вернуть список товаров заказа"""
        try:
            if obj.order_item is not None or not obj.order:
                return None
            
            # Получаем workshop_id из контекста
            workshop_id = self.context.get('workshop_id', 0)
            
            items = []
            workshop_name = obj.workshop.name if obj.workshop else ''
            for it in obj.order.items.all():
                # Фильтруем стеклянные товары для цехов после ID5
                if workshop_id > 5 and it.product and getattr(it.product, 'is_glass', False):
                    continue
                    
                info = it.get_workshop_info(workshop_name)
                # try to resolve product image url
                img_url = None
                try:
                    if it.product and getattr(it.product, 'img', None):
                        img_url = getattr(it.product.img, 'url', None) or str(it.product.img)
                except Exception:
                    img_url = None
                item_data = {
                    'id': it.id,
                    'product': {
                        'id': it.product.id if it.product else None,
                        'name': it.product.name if it.product else 'Не указан',
                        'is_glass': bool(getattr(it.product, 'is_glass', False)) if it.product else False,
                        'img': img_url,
                    },
                    'quantity': it.quantity,
                    'size': info.get('size') if isinstance(info, dict) else it.size,
                    'color': info.get('color') if isinstance(info, dict) else it.color,
                    'display_name': it.get_display_name(),
                }
                # Дополнительные поля если присутствуют
                for k in ['glass_type','paint_type','paint_color','cnc_specs','cutting_specs','preparation_specs','packaging_notes']:
                    v = None
                    if isinstance(info, dict):
                        v = info.get(k)
                    if v is None:
                        v = getattr(it, k, '')
                    if v:
                        item_data[k] = v
                items.append(item_data)
            return items
        except Exception:
            return []
    
    def get_products(self, obj):
        try:
            if obj.order_item is not None or not obj.order:
                return None
            names = []
            for it in obj.order.items.all():
                try:
                    names.append(_safe_str(it.get_display_name()))
                except Exception:
                    names.append('Не указан')
            return ', '.join(names)
        except Exception:
            return None
    
    def get_total_quantity(self, obj):
        try:
            if obj.order_item is not None or not obj.order:
                return None
            return sum((it.quantity or 0) for it in obj.order.items.all())
        except Exception:
            return None
    
    def to_representation(self, instance):
        """Переопределяем для безопасной обработки null значений"""
        data = super().to_representation(instance)
        
        # Получаем workshop_id из контекста
        workshop_id = self.context.get('workshop_id', 0)
        
        # Фильтруем стеклянные товары для цехов после ID5
        if workshop_id > 5:
            # Если order_item является стеклянным товаром, обнуляем его
            if (instance.order_item and 
                instance.order_item.product and 
                getattr(instance.order_item.product, 'is_glass', False)):
                data['order_item'] = None
            
            # Фильтруем стеклянные товары в aggregated_items
            if 'aggregated_items' in data and data['aggregated_items']:
                data['aggregated_items'] = [
                    item for item in data['aggregated_items']
                    if not (item.get('product', {}).get('is_glass', False))
                ]
        
        # Sanitize string fields
        for key in ['operation', 'comment']:
            if key in data:
                data[key] = _safe_str(data.get(key))
        
        # Убеждаемся, что order_item не вызывает ошибок
        if not instance.order_item:
            data['order_item'] = None
        return data


class OrderDefectSerializer(serializers.ModelSerializer):
    workshop = WorkshopFullSerializer(read_only=True)
    class Meta:
        model = OrderDefect
        fields = ['id', 'workshop', 'quantity', 'date', 'comment']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'comment' in data:
            data['comment'] = _safe_str(data.get('comment'))
        return data


class OrderSerializer(serializers.ModelSerializer):
    client = ClientFullSerializer(read_only=True)
    product = ProductFullSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), write_only=True, source='client')
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product', required=False, allow_null=True)
    workshop = WorkshopFullSerializer(read_only=True)
    stages = OrderStageSerializer(many=True, read_only=True)
    defects = OrderDefectSerializer(source='order_defects', many=True, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    items_data = OrderItemSerializer(many=True, write_only=True, required=False, source='items')
    total_done_count = serializers.IntegerField(read_only=True)
    total_defective_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    has_glass_items = serializers.BooleanField(read_only=True)
    glass_items = serializers.SerializerMethodField()
    regular_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'name', 'client', 'client_id', 'workshop', 'product', 'product_id', 
            'quantity', 'status', 'status_display', 'expenses', 'comment', 'created_at', 
            'stages', 'defects', 'items', 'items_data', 'total_done_count', 
            'total_defective_count', 'total_quantity', 'has_glass_items', 'glass_items', 'regular_items'
        ]

    def get_glass_items(self, obj):
        return [OrderItemSerializer(item).data for item in obj.glass_items]

    def get_regular_items(self, obj):
        return [OrderItemSerializer(item).data for item in obj.regular_items]

    def validate(self, attrs):
        # Для создания заказа требуем либо items, либо product+quantity
        if self.instance is None:  # Создание нового заказа
            items = self.initial_data.get('items') or self.initial_data.get('items_data')
            product = attrs.get('product')
            quantity = attrs.get('quantity')
            if not items and not (product and quantity):
                raise serializers.ValidationError('Нужно указать либо product_id и quantity, либо список items.')
        
        # Для обновления заказа валидация не требуется
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        # If items provided, create them; otherwise legacy single product mapping as one item for consistency
        if items_data:
            for item in items_data:
                OrderItem.objects.create(order=order, **item)
            # Ensure stages exist now that we know total quantity
            if not order.stages.exists():
                create_order_stages(order)
        elif order.product and order.quantity:
            OrderItem.objects.create(order=order, product=order.product, quantity=order.quantity)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        # Обновляем основные поля заказа (только те, которые есть в модели)
        allowed_fields = ['name', 'client', 'status', 'comment']
        for attr, value in validated_data.items():
            if attr in allowed_fields and hasattr(instance, attr):
                setattr(instance, attr, value)
        instance.save()
        
        # Обновляем товары заказа только если переданы новые данные
        if items_data is not None:
            # Удаляем старые товары
            instance.items.all().delete()
            # Создаем новые товары
            for item in items_data:
                OrderItem.objects.create(order=instance, **item)
            # Пересоздаем этапы если нужно
            if not instance.stages.exists():
                try:
                    create_order_stages(instance)
                except Exception as e:
                    print(f"Warning: Error creating order stages in serializer: {e}")
                    # Продолжаем выполнение, этапы не критичны
        
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in ['name', 'comment', 'status_display']:
            if key in data:
                data[key] = _safe_str(data.get(key))
        # Sanitize client/product nested names
        if isinstance(data.get('client'), dict) and 'name' in data['client']:
            data['client']['name'] = _safe_str(data['client']['name'])
        if isinstance(data.get('product'), dict) and 'name' in data['product']:
            data['product']['name'] = _safe_str(data['product']['name'])
        return data


class OrderStageConfirmSerializer(serializers.Serializer):
    completed_quantity = serializers.IntegerField(min_value=0) 