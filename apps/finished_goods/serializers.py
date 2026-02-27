from rest_framework import serializers
from .models import FinishedGood, FinishedGoodSale
from apps.clients.models import Client
from apps.orders.models import Order
from apps.products.serializers import ProductSerializer
from apps.orders.serializers import OrderSerializer

class FinishedGoodSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField()
    order = serializers.StringRelatedField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = FinishedGood
        fields = [
            'id', 'product', 'quantity', 'order', 'status', 'status_display',
            'received_at', 'issued_at', 'recipient', 'comment'
        ]

class FinishedGoodDetailSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    order = OrderSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = FinishedGood
        fields = [
            'id', 'product', 'quantity', 'order', 'status', 'status_display',
            'received_at', 'issued_at', 'recipient', 'comment'
        ] 


class FinishedGoodSaleSerializer(serializers.ModelSerializer):
    finished_good_id = serializers.PrimaryKeyRelatedField(
        queryset=FinishedGood.objects.all(),
        source='finished_good',
        write_only=True
    )
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
    quantity = serializers.IntegerField(source='finished_good.quantity', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    order_name = serializers.CharField(source='order.name', read_only=True)

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
            'sold_at',
        ]

    def validate(self, attrs):
        finished_good = attrs.get('finished_good')
        if finished_good and finished_good.status == 'issued':
            raise serializers.ValidationError('Этот товар уже продан или выдан.')
        return attrs
