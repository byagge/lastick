from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from .models import FinishedGood, FinishedGoodSale
from .serializers import FinishedGoodSerializer, FinishedGoodDetailSerializer, FinishedGoodSaleSerializer
from django.views.generic import TemplateView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.utils import timezone
from apps.defects.models import Defect
from datetime import timedelta
import re

# Create your views here.

class FinishedGoodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinishedGood.objects.select_related('product', 'order', 'workshop').all().order_by('-received_at')
    serializer_class = FinishedGoodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Добавляем информацию о браках для каждой записи
        for item in response.data:
            finished_good_id = item.get('id')
            if not finished_good_id:
                continue
            
            try:
                finished_good = FinishedGood.objects.get(id=finished_good_id)
            except FinishedGood.DoesNotExist:
                continue
            
            # Ищем связанный брак для этой готовой продукции
            # Брак создается в тот же день с комментарием об упаковке
            item_date = finished_good.received_at or finished_good.packaging_date
            if not item_date:
                continue
                
            date_start = item_date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            # Ищем брак по продукту и дате, или по комментарию
            # Приоритет: продукт + дата, затем только дата + комментарий
            related_defect = None
            
            # Сначала пытаемся найти по продукту и дате
            if finished_good.product:
                related_defect = Defect.objects.filter(
                    product=finished_good.product,
                    created_at__gte=date_start,
                    created_at__lt=date_end,
                    employee_comment__icontains="Packaging defect"
                ).first()
            
            # Если не нашли, ищем только по дате и комментарию (может быть несколько, берем первый)
            if not related_defect:
                related_defect = Defect.objects.filter(
                    created_at__gte=date_start,
                    created_at__lt=date_end,
                    employee_comment__icontains="Packaging defect"
                ).order_by('-created_at').first()
            
            scrap_quantity = 0
            input_quantity = float(finished_good.quantity)
            
            if related_defect:
                scrap_quantity = float(related_defect.quantity)
                # Из комментария "Packaging defect: X kg of Y kg" извлекаем Y
                comment = related_defect.employee_comment or ""
                match = re.search(r"of\s+([\d.]+)\s+kg", comment)
                if match:
                    input_quantity = float(match.group(1))
                else:
                    # Если не удалось извлечь, считаем что input = produced + scrap
                    input_quantity = float(finished_good.quantity) + scrap_quantity
            
            efficiency = (float(finished_good.quantity) / input_quantity * 100) if input_quantity > 0 else 100.0
            
            item['input_quantity'] = input_quantity
            item['scrap_quantity'] = scrap_quantity
            item['efficiency'] = round(efficiency, 1)
            item['defect_id'] = related_defect.id if related_defect else None
        
        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = FinishedGoodDetailSerializer(instance, context={'request': request})
        return Response(serializer.data)


class FinishedGoodSaleViewSet(viewsets.ModelViewSet):
    queryset = FinishedGoodSale.objects.select_related(
        'finished_good__product',
        'client',
        'order'
    ).all()
    serializer_class = FinishedGoodSaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            sale = serializer.save()
            finished_good = sale.finished_good
            finished_good.status = 'issued'
            finished_good.issued_at = timezone.now()
            finished_good.recipient = sale.client.name
            if sale.order:
                finished_good.order = sale.order
            finished_good.save(update_fields=['status', 'issued_at', 'recipient', 'order'])
        output = self.get_serializer(sale)
        return Response(output.data, status=status.HTTP_201_CREATED)

class FinishedGoodsPageView(TemplateView):
    template_name = 'finished_goods.html'

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['iphone', 'android', 'ipad', 'mobile', 'opera mini', 'blackberry'])
        if is_mobile:
            self.template_name = 'finished_mobile.html'
        else:
            self.template_name = 'finished_goods.html'
        return super().dispatch(request, *args, **kwargs)
