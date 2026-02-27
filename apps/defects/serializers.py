from rest_framework import serializers

from .models import Defect
from apps.products.models import Product
from apps.users.models import User


class ProductShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name"]


class UserShortSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "full_name"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class DefectSerializer(serializers.ModelSerializer):
    product = ProductShortSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        write_only=True,
        required=False,
        allow_null=True,
    )
    user = UserShortSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        write_only=True,
        required=False,
        allow_null=True,
    )
    penalty_assigned_by = UserShortSerializer(read_only=True)

    class Meta:
        model = Defect
        fields = [
            "id",
            "product",
            "product_id",
            "user",
            "user_id",
            "quantity",
            "employee_comment",
            "admin_comment",
            "penalty_amount",
            "penalty_assigned_by",
            "penalty_assigned_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "penalty_amount",
            "penalty_assigned_by",
            "penalty_assigned_at",
            "created_at",
        ]


class DefectPenaltySerializer(serializers.Serializer):
    penalty_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=True,
    )
    admin_comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
    )
