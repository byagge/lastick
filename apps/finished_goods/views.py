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

# Create your views here.

class FinishedGoodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinishedGood.objects.select_related('product', 'order').all().order_by('-received_at')
    serializer_class = FinishedGoodSerializer
    permission_classes = [permissions.IsAuthenticated]

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
