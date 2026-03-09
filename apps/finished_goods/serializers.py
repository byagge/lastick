from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import FinishedGood, FinishedGoodSale
from apps.clients.models import Client
from apps.orders.models import Order
from apps.products.serializers import ProductSerializer
from apps.orders.serializers import OrderSerializer


MONEY_Q = Decimal('0.01')


def qmoney(value: Decimal) -> Decimal:
    return (value or Decimal('0')).quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def _get_cost_breakdown(product, quantity=1):
    if not product:
        return None
    return product.get_cost_breakdown(quantity=quantity)


class FinishedGoodSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField()
    order = serializers.StringRelatedField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    cost_per_unit = serializers.SerializerMethodField()
    cost_total = serializers.SerializerMethodField()

    class Meta:
        model = FinishedGood
        fields = [
            'id', 'product', 'quantity', 'order', 'status', 'status_display',
            'received_at', 'issued_at', 'recipient', 'comment',
            'cost_per_unit', 'cost_total',
        ]

    def get_cost_per_unit(self, obj):
        breakdown = _get_cost_breakdown(getattr(obj, 'product', None), quantity=1)
        if not breakdown:
            return None
        return breakdown["totals"]["total"]

    def get_cost_total(self, obj):
        breakdown = _get_cost_breakdown(getattr(obj, 'product', None), quantity=1)
        if not breakdown:
            return None
        per_unit = breakdown["totals"]["total"]
        return qmoney(Decimal(str(per_unit)) * Decimal(str(obj.quantity or 0)))


class FinishedGoodDetailSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    order = OrderSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    cost_per_unit = serializers.SerializerMethodField()
    cost_total = serializers.SerializerMethodField()
    cost_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = FinishedGood
        fields = [
            'id', 'product', 'quantity', 'order', 'status', 'status_display',
            'received_at', 'issued_at', 'recipient', 'comment',
            'cost_per_unit', 'cost_total', 'cost_breakdown',
        ]

    def get_cost_per_unit(self, obj):
        breakdown = _get_cost_breakdown(getattr(obj, 'product', None), quantity=1)
        if not breakdown:
            return None
        return breakdown["totals"]["total"]

    def get_cost_total(self, obj):
        breakdown = _get_cost_breakdown(getattr(obj, 'product', None), quantity=1)
        if not breakdown:
            return None
        per_unit = breakdown["totals"]["total"]
        return qmoney(Decimal(str(per_unit)) * Decimal(str(obj.quantity or 0)))

    def get_cost_breakdown(self, obj):
        return _get_cost_breakdown(getattr(obj, 'product', None), quantity=obj.quantity or 1)


class FinishedGoodSaleSerializer(serializers.ModelSerializer):
    finished_good_id = serializers.PrimaryKeyRelatedField(
        queryset=FinishedGood.objects.all(),
        source='finished_good',
        write_only=True
    )
    quantity = serializers.IntegerField(min_value=1)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client',
        write_only=True
    )
    order_id = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(),
        source='order',
        write_only=True,
        required=False,
        allow_null=True
    )
    product_name = serializers.CharField(source='finished_good.product.name', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    order_name = serializers.CharField(source='order.name', read_only=True)
    unit_price = serializers.SerializerMethodField()
    cost_per_unit = serializers.SerializerMethodField()
    cost_total = serializers.SerializerMethodField()
    profit_per_unit = serializers.SerializerMethodField()
    profit_total = serializers.SerializerMethodField()

    class Meta:
        model = FinishedGoodSale
        fields = [
            'id',
            'finished_good_id',
            'product_name',
            'quantity',
            'client_id',
            'client_name',
            'order_id',
            'order_name',
            'price',
            'unit_price',
            'cost_per_unit',
            'cost_total',
            'profit_per_unit',
            'profit_total',
            'sold_at',
        ]

    def validate(self, attrs):
        finished_good = attrs.get('finished_good')
        quantity = attrs.get('quantity') or 0
        if finished_good and finished_good.status == 'issued':
            raise serializers.ValidationError('Эта партия уже продана или выдана.')
        if finished_good and quantity > int(finished_good.quantity or 0):
            raise serializers.ValidationError('Количество продажи больше доступного остатка.')
        return attrs

    def get_unit_price(self, obj):
        qty = int(getattr(obj, 'quantity', 0) or 0)
        if qty <= 0:
            return None
        return qmoney(Decimal(str(obj.price)) / Decimal(str(qty)))

    def get_cost_per_unit(self, obj):
        product = getattr(getattr(obj, 'finished_good', None), 'product', None)
        breakdown = _get_cost_breakdown(product, quantity=1)
        if not breakdown:
            return None
        return breakdown["totals"]["total"]

    def get_cost_total(self, obj):
        per_unit = self.get_cost_per_unit(obj)
        if per_unit is None:
            return None
        qty = Decimal(str(getattr(obj, 'quantity', 0) or 0))
        return qmoney(Decimal(str(per_unit)) * qty)

    def get_profit_per_unit(self, obj):
        unit_price = self.get_unit_price(obj)
        cost_per_unit = self.get_cost_per_unit(obj)
        if unit_price is None or cost_per_unit is None:
            return None
        return qmoney(Decimal(str(unit_price)) - Decimal(str(cost_per_unit)))

    def get_profit_total(self, obj):
        cost_total = self.get_cost_total(obj)
        if cost_total is None:
            return None
        return qmoney(Decimal(str(obj.price)) - Decimal(str(cost_total)))
