from django.shortcuts import render
from django.db.models import Sum
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Defect
from .serializers import DefectSerializer, DefectPenaltySerializer
from apps.users.models import User


def defects_page(request):
    return render(request, "defects.html")


def defects_mobile_page(request):
    return render(request, "defects_mobile.html")


class DefectViewSet(viewsets.ModelViewSet):
    queryset = Defect.objects.select_related(
        "product",
        "user",
        "penalty_assigned_by",
    ).all()
    serializer_class = DefectSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()

        product_filter = self.request.query_params.get("product")
        if product_filter:
            queryset = queryset.filter(product_id=product_filter)

        user_filter = self.request.query_params.get("user")
        if user_filter:
            queryset = queryset.filter(user_id=user_filter)

        return queryset.order_by("-created_at")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_penalty(request, defect_id):
    try:
        defect = Defect.objects.select_related("user").get(id=defect_id)
    except Defect.DoesNotExist:
        return Response({"error": "Брак не найден"}, status=status.HTTP_404_NOT_FOUND)

    if request.user.role not in [User.Role.ADMIN, User.Role.ACCOUNTANT]:
        return Response(
            {"error": "Недостаточно прав для назначения штрафа"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = DefectPenaltySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    defect.apply_penalty(
        amount=data.get("penalty_amount"),
        assigned_by=request.user,
        admin_comment=data.get("admin_comment", ""),
    )

    return Response({"success": True, "defect": DefectSerializer(defect).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def defects_stats(request):
    total_defects = Defect.objects.count()
    total_quantity = (
        Defect.objects.aggregate(total=Sum("quantity")).get("total") or 0
    )
    total_penalty = (
        Defect.objects.aggregate(total=Sum("penalty_amount")).get("total") or 0
    )
    with_penalty = Defect.objects.filter(penalty_amount__isnull=False).count()

    return Response(
        {
            "total_defects": total_defects,
            "total_quantity": float(total_quantity),
            "total_penalty": float(total_penalty),
            "with_penalty": with_penalty,
        }
    )
