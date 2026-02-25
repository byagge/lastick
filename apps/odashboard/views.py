from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from apps.users.models import User
from apps.operations.workshops.models import Workshop
from apps.employee_tasks.models import EmployeeTask
from apps.defects.models import Defect
from apps.orders.models import OrderStage

# Create your views here.

@login_required
def dashboard(request):
    user = request.user
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])
    role = getattr(user, 'role', None)
    # Admin: use operations dashboard templates
    if role == User.Role.ADMIN:
        template = 'odashboard_mobile.html' if is_mobile else 'odashboard.html'
        return render(request, template)

    # Accountant: redirect to finance
    elif role == User.Role.ACCOUNTANT:
        return redirect('/finance/')

    # Worker: redirect to employee tasks
    elif role == User.Role.WORKER:
        return redirect('/employee_tasks/tasks/')

    # No access otherwise
    return HttpResponseForbidden('??? ???????')


def workshop_dashboard(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone'])
    template = 'workshop_mobile.html' if is_mobile else 'workshop_master.html'
    return render(request, template)


@login_required
def workshop_dashboard_overview(request):
    """API endpoint для получения обзора цеха"""
    try:
        user = request.user
        workshop = getattr(user, 'workshop', None)
        
        if not workshop:
            return JsonResponse({
                'error': 'Цех не назначен'
            }, status=400)
        
        # Подсчитываем сотрудников в цехе
        total_employees = User.objects.filter(workshop=workshop, role__in=['worker']).count()
        
        # Подсчитываем произведенные товары (завершенные задачи)
        products_made = EmployeeTask.objects.filter(
            stage__workshop=workshop,
            completed_quantity__gt=0
        ).aggregate(total=Sum('completed_quantity'))['total'] or 0
        
        # Подсчитываем браки
        defective_products = Defect.objects.filter(
            user__workshop=workshop
        ).count()
        
        # Подсчитываем активные заказы
        active_orders = OrderStage.objects.filter(
            workshop=workshop,
            status__in=['in_progress', 'partial']
        ).values('order').distinct().count()
        
        return JsonResponse({
            'workshop_name': workshop.name,
            'user_name': user.get_full_name() or user.username,
            'total_employees': total_employees,
            'products_made': products_made,
            'defective_products': defective_products,
            'active_orders': active_orders
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def workshop_production_chart(request):
    """API endpoint для получения графика производства"""
    try:
        user = request.user
        workshop = getattr(user, 'workshop', None)
        
        if not workshop:
            return JsonResponse({
                'error': 'Цех не назначен'
            }, status=400)
        
        period = request.GET.get('period', 'week')
        
        # Определяем период
        if period == 'week':
            days = 7
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days-1)
            date_format = '%a'  # Mon, Tue, etc.
        elif period == 'month':
            days = 30
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days-1)
            date_format = '%d'  # Day of month
        elif period == 'year':
            days = 12
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=365)
            date_format = '%b'  # Jan, Feb, etc.
        else:
            period = 'week'
            days = 7
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days-1)
            date_format = '%a'
        
        # Генерируем метки для графика
        labels = []
        products_data = []
        defective_data = []
        
        current_date = start_date
        for i in range(days):
            if period == 'week':
                labels.append(current_date.strftime(date_format))
            elif period == 'month':
                labels.append(str(current_date.day))
            else:  # year
                labels.append(current_date.strftime(date_format))
            
            # Подсчитываем данные за день
            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))
            
            # Произведенные товары за день
            daily_products = EmployeeTask.objects.filter(
                stage__workshop=workshop,
                completed_at__gte=day_start,
                completed_at__lte=day_end
            ).aggregate(total=Sum('completed_quantity'))['total'] or 0
            
            # Браки за день
            daily_defective = Defect.objects.filter(
                user__workshop=workshop,
                created_at__gte=day_start,
                created_at__lte=day_end
            ).count()
            
            products_data.append(daily_products)
            defective_data.append(daily_defective)
            
            current_date += timedelta(days=1)
        
        return JsonResponse({
            'labels': labels,
            'products': products_data,
            'defective': defective_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def maintenance(request):
    """Страница технического обслуживания"""
    return render(request, 'maintenance.html')
