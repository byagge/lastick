from rest_framework import serializers

from .models import Defect, DefectRework
from apps.products.models import Product
from apps.users.models import User
from apps.inventory.models import RawMaterial


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
    available_for_rework = serializers.SerializerMethodField()

    class Meta:
        model = Defect
        fields = [
            "id",
            "product",
            "product_id",
            "user",
            "user_id",
            "quantity",
            "available_for_rework",
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

    def get_available_for_rework(self, obj):
        return float(obj.available_for_rework)


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


class RawMaterialShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = ["id", "name", "unit"]


class DefectReworkSerializer(serializers.ModelSerializer):
    raw_material = RawMaterialShortSerializer(read_only=True)
    employee = UserShortSerializer(read_only=True)

    class Meta:
        model = DefectRework
        fields = [
            "id",
            "raw_material",
            "input_quantity",
            "output_quantity",
            "comment",
            "employee",
            "created_at",
        ]


class DefectReworkCreateSerializer(serializers.Serializer):
    raw_material_id = serializers.PrimaryKeyRelatedField(
        queryset=RawMaterial.objects.all(), source="raw_material"
    )
    input_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=0.001,
        help_text="Сколько брака переработать (кг)",
    )
    output_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=0,
        help_text="Сколько сырья получится (кг)",
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        defect = self.context.get("defect")
        if defect is None:
            raise serializers.ValidationError("Не передан объект брака для переработки.")

        input_quantity = attrs.get("input_quantity")
        if input_quantity is None:
            raise serializers.ValidationError(
                {"input_quantity": "Это поле обязательно."}
            )

        remaining = defect.available_for_rework
        if input_quantity > remaining:
            raise serializers.ValidationError(
                {
                    "input_quantity": (
                        f"Нельзя переработать больше, чем осталось брака "
                        f"({float(remaining)} кг)."
                    )
                }
            )
        return attrs
