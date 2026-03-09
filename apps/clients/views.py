from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db import models

from apps.clients.models import Client
from .serializers import ClientSerializer
from apps.orders.models import Order
from apps.finance.models import Request, Debt

# Create your views here.

# API: Список и создание клиентов
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('-created_at')
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(phone__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(company__icontains=search)
            )
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    @action(detail=True, methods=['get'], url_path='details')
    def details(self, request, pk=None):
        """
        Расширенная информация по клиенту:
        - все заказы клиента
        - оборот по заказам
        - средний чек
        - заявки из финансового модуля
        """
        client = self.get_object()

        # Заказы клиента
        orders_qs = (
            Order.objects.filter(client=client)
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

        orders_data = []
        total_turnover = 0
        total_quantity = 0

        for order in orders_qs:
            order_total = 0
            for item in order.items.all():
                product = getattr(item, 'product', None)
                price = getattr(product, 'price', 0) or 0
                qty = item.quantity or 0
                order_total += qty * price
                total_quantity += qty

            total_turnover += order_total

            orders_data.append({
                'id': order.id,
                'name': str(order),
                'status': order.status,
                'status_display': getattr(order, 'status_display', order.status),
                'created_at': order.created_at,
                'total_quantity': getattr(order, 'total_quantity', None) or 0,
                'total_price': order_total,
            })

        orders_count = len(orders_data)
        average_check = float(total_turnover / orders_count) if orders_count else 0

        # Заявки из finance.Request
        from django.db.models import Sum

        requests_qs = Request.objects.filter(client=client)
        agg = requests_qs.aggregate(total=Sum('total_amount'))
        requests_total = agg.get('total') or 0
        requests_count = requests_qs.count()

        debts_qs = Debt.objects.filter(client=client).order_by('-created_at', '-id')
        debts_data = []
        total_debt_original = 0
        total_debt_paid = 0
        total_debt_outstanding = 0

        for debt in debts_qs:
            outstanding_amount = debt.outstanding_amount
            total_debt_original += debt.original_amount or 0
            total_debt_paid += debt.amount_paid or 0
            total_debt_outstanding += outstanding_amount or 0
            debts_data.append({
                'id': debt.id,
                'title': debt.title,
                'direction': debt.direction,
                'status': debt.status,
                'original_amount': debt.original_amount,
                'amount_paid': debt.amount_paid,
                'outstanding_amount': outstanding_amount,
                'due_date': debt.due_date,
                'created_at': debt.created_at,
            })

        client_data = ClientSerializer(client).data
        client_data.update({
            'orders': orders_data,
            'orders_count': orders_count,
            'orders_total_quantity': total_quantity,
            'total_turnover': total_turnover,
            'average_check': average_check,
            # Для мобильного шаблона
            'total_spent': total_turnover,
            # Инфо по заявкам (продажи через finance)
            'requests_total_amount': requests_total,
            'requests_count': requests_count,
            'debts': debts_data,
            'debts_count': len(debts_data),
            'debts_total_original': total_debt_original,
            'debts_total_paid': total_debt_paid,
            'debts_total_outstanding': total_debt_outstanding,
        })
        return Response(client_data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=201)
        print('CLIENT CREATE ERROR:', serializer.errors, 'DATA:', request.data)
        return Response(serializer.errors, status=400)

def clients_page(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile'])
    template = 'clients_mobile.html' if is_mobile else 'clients.html'
    return render(request, template)
