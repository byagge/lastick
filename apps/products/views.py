from django.views import View
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Product
from .serializers import ProductSerializer
from apps.users.models import User


class IsAdminOrAccountant(permissions.BasePermission):
    """
    Запрещает изменяющие операции всем, кроме admin/accountant/superuser.
    """

    def has_permission(self, request, view):
        user = request.user
        role = getattr(user, 'role', None)
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or role in [User.Role.ADMIN, User.Role.ACCOUNTANT])
        )

class ProductViewSet(viewsets.ModelViewSet):
    queryset = (
        Product.objects.all()
        .prefetch_related('services', 'services__service_materials__material')
        .order_by('name', 'id')
    )
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Просмотр доступен всем авторизованным.
        # Создание/изменение/удаление — только admin/accountant/superuser.
        if getattr(self, 'action', None) in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsAdminOrAccountant()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def costing(self, request, pk=None):
        """
        Детализация себестоимости продукта.

        Query params:
        - quantity: int (по умолчанию 1)
        - as_of: YYYY-MM-DD (опционально, влияет на распределение накладных из finance)
        """
        product = self.get_object()
        try:
            quantity = int(request.query_params.get('quantity') or 1)
        except Exception:
            quantity = 1

        as_of = request.query_params.get('as_of')
        if as_of:
            try:
                from datetime import date
                as_of_date = date.fromisoformat(as_of)
            except Exception:
                as_of_date = None
        else:
            as_of_date = None

        bd = product.get_cost_breakdown(quantity=quantity)
        # если передали as_of — пересчитаем с ним (финансовое распределение)
        if as_of_date:
            from .costing import calculate_product_cost
            bd = calculate_product_cost(product, quantity=quantity, as_of=as_of_date)

        # Decimal -> float для JSON
        from decimal import Decimal
        def convert(x):
            if isinstance(x, Decimal):
                return float(x)
            if isinstance(x, dict):
                return {k: convert(v) for k, v in x.items()}
            if isinstance(x, list):
                return [convert(v) for v in x]
            return x

        return Response(convert(bd))

class ProductsPageView(View):
    def get(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['iphone', 'android', 'ipad', 'mobile'])
        template = 'products_mobile.html' if is_mobile else 'products.html'
        return render(request, template)
