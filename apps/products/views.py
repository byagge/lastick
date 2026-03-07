from django.views import View
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import permissions
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
    queryset = Product.objects.all().prefetch_related('services').order_by('name', 'id')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Просмотр доступен всем авторизованным.
        # Создание/изменение/удаление — только admin/accountant/superuser.
        if getattr(self, 'action', None) in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsAdminOrAccountant()]
        return [permissions.IsAuthenticated()]

class ProductsPageView(View):
    def get(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['iphone', 'android', 'ipad', 'mobile'])
        template = 'products_mobile.html' if is_mobile else 'products.html'
        return render(request, template)
