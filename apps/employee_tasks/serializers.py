from rest_framework import serializers
from .models import EmployeeTask

class EmployeeTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    done_quantity = serializers.SerializerMethodField()
    stage_name = serializers.CharField(source='stage.operation', read_only=True)
    order_item = serializers.SerializerMethodField()
    workshop_info = serializers.SerializerMethodField()
    is_completed = serializers.BooleanField(read_only=True)
    title = serializers.CharField(read_only=True)
    plan_quantity = serializers.IntegerField(read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = EmployeeTask
        fields = [
            'id', 'stage', 'employee', 'employee_name', 'quantity', 'completed_quantity', 
            'defective_quantity', 'done_quantity', 'stage_name', 'order_item', 'workshop_info',
            'created_at', 'completed_at', 'earnings', 'penalties', 'net_earnings',
            'is_completed', 'title', 'plan_quantity', 'started_at',
            'custom_unit_price', 'layers_per_unit'
        ]

    def get_done_quantity(self, obj):
        # Если задача выполнена, считаем всё количество сделанным, иначе 0
        return obj.quantity if getattr(obj, 'is_completed', False) else 0

    def get_employee_name(self, obj):
        if obj.employee:
            # Попробовать get_full_name, иначе first_name + last_name, иначе username
            if hasattr(obj.employee, 'get_full_name'):  
                name = obj.employee.get_full_name()
                if name:
                    return name
            first = getattr(obj.employee, 'first_name', '')
            last = getattr(obj.employee, 'last_name', '')
            if first or last:
                return f'{first} {last}'.strip()
            return getattr(obj.employee, 'username', str(obj.employee.pk))
        return ''
    
    def get_order_item(self, obj):
        """Возвращает сериализованный order_item с полной информацией о товаре"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== DEBUG SERIALIZER: get_order_item for EmployeeTask {obj.id} ===")
        
        # Получаем объект stage, если это ID
        stage_obj = obj.stage
        if hasattr(stage_obj, 'id') and not hasattr(stage_obj, 'order_item'):
            # Если stage это ID, нужно получить объект
            from apps.orders.models import OrderStage
            try:
                stage_obj = OrderStage.objects.select_related('order_item__product', 'order__client').get(id=stage_obj)
                logger.info(f"Retrieved stage object: {stage_obj}")
            except OrderStage.DoesNotExist:
                logger.error(f"Stage with ID {stage_obj} not found")
                return None
        
        logger.info(f"Stage object: {stage_obj}")
        logger.info(f"Stage order_item: {getattr(stage_obj, 'order_item', None) if stage_obj else None}")
        logger.info(f"Stage order: {getattr(stage_obj, 'order', None) if stage_obj else None}")
        
        if stage_obj and stage_obj.order_item:
            # Если есть прямая связь с order_item
            logger.info("Using direct order_item connection")
            from apps.orders.serializers import OrderItemSerializer
            result = OrderItemSerializer(stage_obj.order_item).data
            logger.info(f"Direct order_item data: {result}")
            return result
        elif stage_obj and stage_obj.order:
            # Fallback: если order_item равен null, пытаемся получить данные через заказ
            logger.info("Using fallback through order")
            from apps.orders.models import OrderItem
            from apps.orders.serializers import OrderItemSerializer
            
            # Ищем позиции заказа для этого заказа
            order_items = OrderItem.objects.filter(order=stage_obj.order)
            logger.info(f"Found {order_items.count()} order items for order {stage_obj.order.id}")
            
            if order_items.exists():
                # Берем первую позицию (обычно их одна для простых заказов)
                first_item = order_items.first()
                logger.info(f"Using first order item: {first_item}")
                item_data = OrderItemSerializer(first_item).data
                
                # Добавляем информацию о заказе
                # Также включаем список всех товаров заказа, чтобы фронт мог отобразить их
                items_list = []
                try:
                    for it in order_items:
                        items_list.append({
                            'id': it.id,
                            'quantity': it.quantity,
                            'size': it.size,
                            'color': it.color,
                            'display_name': it.get_display_name() if hasattr(it, 'get_display_name') else (it.product.name if it.product else 'Не указан'),
                            'product': {
                                'id': it.product.id if it.product else None,
                                'name': it.product.name if it.product else 'Не указан',
                                'is_glass': it.product.is_glass if it.product else False
                            } if it.product else None
                        })
                except Exception:
                    items_list = []
                
                item_data['order'] = {
                    'id': stage_obj.order.id,
                    'name': stage_obj.order.name,
                    'status': stage_obj.order.status,
                    'status_display': stage_obj.order.get_status_display(),
                    'created_at': stage_obj.order.created_at.isoformat() if stage_obj.order.created_at else None,
                    'client': {
                        'name': stage_obj.order.client.name if stage_obj.order.client else 'Не указан'
                    } if stage_obj.order.client else None,
                    'items': items_list
                }
                
                logger.info(f"Fallback order_item data: {item_data}")
                return item_data
            else:
                logger.info("No order items found for this order")
        else:
            logger.info("No stage or order available")
        
        logger.info("Returning None for order_item")
        return None
    
    def get_workshop_info(self, obj):
        """Возвращает информацию для цеха"""
        # Получаем объект stage, если это ID
        stage_obj = obj.stage
        if hasattr(stage_obj, 'id') and not hasattr(stage_obj, 'get_workshop_info'):
            # Если stage это ID, нужно получить объект
            from apps.orders.models import OrderStage
            try:
                stage_obj = OrderStage.objects.select_related('workshop').get(id=stage_obj)
            except OrderStage.DoesNotExist:
                return {}
        
        return stage_obj.get_workshop_info() if stage_obj else {} 