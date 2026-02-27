from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Workshop
from .serializers import WorkshopSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

# Create your views here.

class WorkshopViewSet(viewsets.ModelViewSet):
	queryset = Workshop.objects.all().order_by('name', 'id')
	serializer_class = WorkshopSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ['name', 'description']
	ordering_fields = ['name', 'created_at']

def _get_active_workshops(limit=2):
	return Workshop.objects.filter(is_active=True).order_by('id')[:limit]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshop_orders_info(request, workshop_id):
	"""
	Получает информацию о заказах в конкретном цехе с полной информацией о товарах
	"""
	try:
		workshop = Workshop.objects.get(id=workshop_id)
		orders_info = workshop.get_orders_info()
		workshop_summary = workshop.get_workshop_summary()
		
		return Response({
			'workshop': workshop_summary,
			'orders': orders_info
		})
	except Workshop.DoesNotExist:
		return Response({'error': 'Цех не найден'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_workshops_orders_info(request):
	"""
	Получает информацию о заказах во всех цехах
	"""
	workshops = _get_active_workshops()
	result = []
	
	for workshop in workshops:
		workshop_summary = workshop.get_workshop_summary()
		orders_info = workshop.get_orders_info()
		
		result.append({
			'workshop': workshop_summary,
			'orders': orders_info
		})
	
	return Response(result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshops_stats(request):
	"""
	Получает статистику по цехам и общую статистику (для первых 2 активных цехов).
	"""
	from apps.employee_tasks.models import EmployeeTask
	from apps.defects.models import Defect
	from django.utils import timezone
	from datetime import timedelta

	workshops = list(_get_active_workshops())
	now = timezone.now()
	week_ago = now - timedelta(days=7)
	month_ago = now - timedelta(days=30)

	if workshops:
		total_stats = _calculate_total_stats(workshops, week_ago, month_ago)
	else:
		total_stats = {
			'total_workshops': 0,
			'total_employees': 0,
			'week_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
			'month_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
			'total_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
		}

	workshops_stats = []
	for workshop in workshops:
		stats = _calculate_workshop_stats(workshop, week_ago, month_ago)
		stats['manager_name'] = workshop.manager.get_full_name() if workshop.manager else 'Цех не назначен'
		stats['active_tasks'] = EmployeeTask.objects.filter(stage__workshop=workshop).count()
		stats['defects'] = Defect.objects.filter(user__workshop=workshop).count()
		stats['summary'] = workshop.get_workshop_summary()
		workshops_stats.append(stats)

	return Response({
		'total_stats': total_stats,
		'workshops': workshops_stats,
	})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshop_masters(request):
	"""Получает список всех мастеров конкретного цеха"""
	workshop_id = request.GET.get('workshop')
	if not workshop_id:
		return Response({'error': 'Не указан ID цеха'}, status=400)
	
	try:
		workshop = Workshop.objects.get(id=workshop_id, is_active=True)
	except Workshop.DoesNotExist:
		return Response({'error': 'Цех не найден'}, status=404)
	
	# Получаем всех мастеров цеха
	all_masters = workshop.get_all_masters()
	masters_data = []
	
	# Главный мастер
	if workshop.manager:
		masters_data.append({
			'id': workshop.manager.id,
			'name': workshop.manager.get_full_name(),
			'role': 'main_manager',
			'can_remove': False
		})
	
	# Дополнительные мастера
	additional_masters = workshop.workshop_masters.filter(is_active=True).select_related('master')
	for wm in additional_masters:
		masters_data.append({
			'id': wm.master.id,
			'name': wm.master.get_full_name(),
			'role': 'additional_master',
			'can_remove': True,
			'added_at': wm.added_at,
			'notes': wm.notes
		})
	
	return Response(masters_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshop_employees(request):
	"""Получает список сотрудников цеха"""
	workshop_id = request.GET.get('workshop')
	if not workshop_id:
		return Response({'error': 'Не указан ID цеха'}, status=400)
	
	try:
		workshop = Workshop.objects.get(id=workshop_id, is_active=True)
		employees = workshop.users.all()
		employees_data = [{'id': e.id, 'name': e.get_full_name()} for e in employees]
		return Response(employees_data)
	except Workshop.DoesNotExist:
		return Response({'error': 'Цех не найден'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_workshop_master(request):
	"""Добавляет дополнительного мастера к цеху"""
	workshop_id = request.data.get('workshop_id')
	master_id = request.data.get('master_id')
	
	if not workshop_id or not master_id:
		return Response({'error': 'Не указаны ID цеха или мастера'}, status=400)
	
	try:
		workshop = Workshop.objects.get(id=workshop_id, is_active=True)
		from apps.users.models import User
		master = User.objects.get(id=master_id)
	except (Workshop.DoesNotExist, User.DoesNotExist):
		return Response({'error': 'Цех или мастер не найден'}, status=404)
	
	# Добавляем мастера
	success, message = workshop.add_master(master)
	
	if success:
		return Response({'message': message, 'success': True})
	else:
		return Response({'error': message}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_workshop_master(request):
	"""Удаляет дополнительного мастера из цеха"""
	workshop_id = request.data.get('workshop_id')
	master_id = request.data.get('master_id')
	
	if not workshop_id or not master_id:
		return Response({'error': 'Не указаны ID цеха или мастера'}, status=400)
	
	try:
		workshop = Workshop.objects.get(id=workshop_id, is_active=True)
		from apps.users.models import User
		master = User.objects.get(id=master_id)
	except (Workshop.DoesNotExist, User.DoesNotExist):
		return Response({'error': 'Цех или мастер не найден'}, status=404)
	
	# Удаляем мастера
	success, message = workshop.remove_master(master)
	
	if success:
		return Response({'message': message, 'success': True})
	else:
		return Response({'error': message}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def master_workshops_stats(request):
	"""Получает статистику по всем цехам мастера"""
	from apps.employee_tasks.models import EmployeeTask
	from django.db.models import Sum
	from django.utils import timezone
	from datetime import timedelta
	
	user = request.user
	
	# Получаем все цеха мастера
	master_workshops = []
	
	# Цеха, где пользователь является главным мастером
	managed_workshops = user.operation_managed_workshops.filter(is_active=True)
	for workshop in managed_workshops:
		master_workshops.append(workshop)
	
	# Цеха, где пользователь является дополнительным мастером
	additional_workshops = user.workshop_master_roles.filter(is_active=True, workshop__is_active=True).select_related('workshop')
	for workshop_master in additional_workshops:
		master_workshops.append(workshop_master.workshop)
	
	# Убираем дубликаты
	master_workshops = list(set(master_workshops))
	
	# Периоды для статистики
	now = timezone.now()
	week_ago = now - timedelta(days=7)
	month_ago = now - timedelta(days=30)
	
	# Общая статистика по всем цехам мастера
	total_stats = _calculate_total_stats(master_workshops, week_ago, month_ago)
	
	# Статистика по каждому цеху
	workshops_stats = []
	for workshop in master_workshops:
		workshop_stats = _calculate_workshop_stats(workshop, week_ago, month_ago)
		workshops_stats.append(workshop_stats)
	
	return Response({
		'total_stats': total_stats,
		'workshops': workshops_stats
	})

def _calculate_total_stats(workshops, week_ago, month_ago):
	"""Рассчитывает общую статистику по всем цехам мастера"""
	from apps.employee_tasks.models import EmployeeTask
	from django.db.models import Sum
	
	# Получаем все задачи по цехам мастера
	workshop_ids = [w.id for w in workshops]
	all_tasks = EmployeeTask.objects.filter(stage__workshop_id__in=workshop_ids)
	
	# Статистика за неделю
	week_tasks = all_tasks.filter(created_at__gte=week_ago)
	week_completed = week_tasks.aggregate(
		total=Sum('completed_quantity'),
		defects=Sum('defective_quantity')
	)
	
	# Статистика за месяц
	month_tasks = all_tasks.filter(created_at__gte=month_ago)
	month_completed = month_tasks.aggregate(
		total=Sum('completed_quantity'),
		defects=Sum('defective_quantity')
	)
	
	# Общая статистика
	total_completed = all_tasks.aggregate(
		total=Sum('completed_quantity'),
		defects=Sum('defective_quantity')
	)
	
	# Количество сотрудников
	total_employees = sum(w.users.count() for w in workshops)
	
	# Эффективность (процент выполненных задач без брака)
	total_quantity = all_tasks.aggregate(total=Sum('quantity'))['total'] or 0
	total_completed_quantity = total_completed['total'] or 0
	total_defects = total_completed['defects'] or 0
	
	efficiency = 0
	if total_quantity > 0:
		efficiency = round(((total_completed_quantity - total_defects) / total_quantity) * 100, 1)
	
	return {
		'total_workshops': len(workshops),
		'total_employees': total_employees,
		'week_stats': {
			'completed_works': week_completed['total'] or 0,
			'defects': week_completed['defects'] or 0,
			'efficiency': _calculate_efficiency(week_completed['total'] or 0, week_completed['defects'] or 0)
		},
		'month_stats': {
			'completed_works': month_completed['total'] or 0,
			'defects': month_completed['defects'] or 0,
			'efficiency': _calculate_efficiency(month_completed['total'] or 0, month_completed['defects'] or 0)
		},
		'total_stats': {
			'completed_works': total_completed_quantity,
			'defects': total_defects,
			'efficiency': efficiency
		}
	}

def _calculate_workshop_stats(workshop, week_ago, month_ago):
	"""Рассчитывает статистику по конкретному цеху"""
	from apps.employee_tasks.models import EmployeeTask
	from django.db.models import Sum
	
	# Получаем задачи цеха
	workshop_tasks = EmployeeTask.objects.filter(stage__workshop=workshop)
	
	# Статистика за неделю
	week_tasks = workshop_tasks.filter(created_at__gte=week_ago)
	week_completed = week_tasks.aggregate(
		total=Sum('completed_quantity'),
		defects=Sum('defective_quantity')
	)
	
	# Статистика за месяц
	month_tasks = workshop_tasks.filter(created_at__gte=month_ago)
	month_completed = month_tasks.aggregate(
		total=Sum('completed_quantity'),
		defects=Sum('defective_quantity')
	)
	
	# Общая статистика
	total_completed = workshop_tasks.aggregate(
		total=Sum('completed_quantity'),
		defects=Sum('defective_quantity')
	)
	
	# Количество сотрудников
	employees_count = workshop.users.count()
	
	# Эффективность
	total_quantity = workshop_tasks.aggregate(total=Sum('quantity'))['total'] or 0
	total_completed_quantity = total_completed['total'] or 0
	total_defects = total_completed['defects'] or 0
	
	efficiency = 0
	if total_quantity > 0:
		efficiency = round(((total_completed_quantity - total_defects) / total_quantity) * 100, 1)
	
	return {
		'id': workshop.id,
		'name': workshop.name,
		'description': workshop.description,
		'employees_count': employees_count,
		'week_stats': {
			'completed_works': week_completed['total'] or 0,
			'defects': week_completed['defects'] or 0,
			'efficiency': _calculate_efficiency(week_completed['total'] or 0, week_completed['defects'] or 0)
		},
		'month_stats': {
			'completed_works': month_completed['total'] or 0,
			'defects': month_completed['defects'] or 0,
			'efficiency': _calculate_efficiency(month_completed['total'] or 0, month_completed['defects'] or 0)
		},
		'total_stats': {
			'completed_works': total_completed_quantity,
			'defects': total_defects,
			'efficiency': efficiency
		}
	}

def _calculate_efficiency(completed, defects):
	"""Рассчитывает эффективность в процентах"""
	if completed == 0:
		return 0
	return round(((completed - defects) / completed) * 100, 1)

def workshops_page(request):
	return render(request, 'workshops.html')

def workshops_mobile_page(request):
	return render(request, 'workshops_mobile.html')

def workshops_list(request):
	from apps.employee_tasks.models import EmployeeTask
	from apps.defects.models import Defect
	from apps.orders.models import OrderStage
	from django.db.models import Q, Count, Avg, Sum
	
	# Простая проверка мобильного устройства по User-Agent
	user_agent = request.META.get('HTTP_USER_AGENT', '')
	ua_lower = user_agent.lower()
	is_mobile = any(token in ua_lower for token in ['mobile', 'android', 'iphone', 'ipad'])
	if is_mobile:
		return render(request, 'workshops_mobile.html')
	
	# Получаем первые 2 активных цеха с предзагрузкой связанных данных
	workshops = list(_get_active_workshops().prefetch_related(
		'users',
		'workshop_masters__master',
		'manager'
	))
	
	# Подготавливаем данные для каждого цеха
	workshops_data = []
	from django.utils import timezone
	from datetime import timedelta
	now = timezone.now()
	week_ago = now - timedelta(days=7)
	month_ago = now - timedelta(days=30)

	for workshop in workshops:
		try:
			workshop_stats = _calculate_workshop_stats(workshop, week_ago, month_ago)
			workshop_summary = workshop.get_workshop_summary()
			# Подсчитываем сотрудников в цехе
			employees_count = workshop_stats.get('employees_count', workshop.users.count())
			
			# Подсчитываем активные задачи
			active_tasks = EmployeeTask.objects.filter(stage__workshop=workshop).count()
			
			# Подсчитываем браки
			defects = Defect.objects.filter(user__workshop=workshop).count()
			
			# Вычисляем производительность на основе выполненных задач
			completed_tasks = EmployeeTask.objects.filter(
				stage__workshop=workshop,
				completed_quantity__gt=0
			).aggregate(total=Sum('completed_quantity'))['total'] or 0
			
			productivity = completed_tasks if completed_tasks > 0 else 0
			
			# Создаем график производительности (реальные данные за последние 7 дней)
			productivity_chart = []
			
			for i in range(7):
				date = now - timedelta(days=i)
				daily_completed = EmployeeTask.objects.filter(
					stage__workshop=workshop,
					completed_at__date=date.date()
				).aggregate(total=Sum('completed_quantity'))['total'] or 0
				
				# Нормализуем значение от 1 до 7 для графика
				if daily_completed == 0:
					productivity_chart.insert(0, 1)
				elif daily_completed <= 5:
					productivity_chart.insert(0, 2)
				elif daily_completed <= 10:
					productivity_chart.insert(0, 3)
				elif daily_completed <= 15:
					productivity_chart.insert(0, 4)
				elif daily_completed <= 20:
					productivity_chart.insert(0, 5)
				elif daily_completed <= 25:
					productivity_chart.insert(0, 6)
				else:
					productivity_chart.insert(0, 7)
			
			# Получаем информацию о мастерах
			workshop_masters = workshop.workshop_masters.filter(is_active=True)
			
			workshops_data.append({
				'id': workshop.id,
				'name': workshop.name,
				'description': workshop.description,
				'manager': workshop.manager.get_full_name() if workshop.manager else 'Не назначен',
				'created_at': workshop.created_at,
				'updated_at': workshop.updated_at,
				'employees_count': employees_count,
				'active_tasks': active_tasks,
				'defects': defects,
				'productivity': productivity,
				'productivity_chart': productivity_chart,
				'workshop_masters': workshop_masters,
				'week_stats': workshop_stats.get('week_stats', {}),
				'month_stats': workshop_stats.get('month_stats', {}),
				'total_stats': workshop_stats.get('total_stats', {}),
				'summary': workshop_summary,
			})
		except Exception as e:
			print(f"Ошибка при обработке цеха {workshop.id}: {e}")
			# Добавляем цех с базовыми данными в случае ошибки
			workshops_data.append({
				'id': workshop.id,
				'name': workshop.name,
				'description': workshop.description or 'Описание отсутствует',
				'manager': 'Не назначен',
				'created_at': workshop.created_at,
				'updated_at': workshop.updated_at,
				'employees_count': 0,
				'active_tasks': 0,
				'defects': 0,
				'productivity': 0,
				'productivity_chart': [1, 1, 1, 1, 1, 1, 1],
				'workshop_masters': [],
				'week_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
				'month_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
				'total_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
				'summary': {},
			})
	
	# Общая статистика
	total_workshops = len(workshops_data)
	total_employees = sum(w['employees_count'] for w in workshops_data)
	total_active_tasks = sum(w['active_tasks'] for w in workshops_data)
	avg_productivity = sum(w['productivity'] for w in workshops_data) // max(total_workshops, 1)

	total_stats = _calculate_total_stats(workshops, week_ago, month_ago) if workshops else {
		'total_workshops': 0,
		'total_employees': 0,
		'week_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
		'month_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
		'total_stats': {'completed_works': 0, 'defects': 0, 'efficiency': 0},
	}

	context = {
		'workshops': workshops_data,
		'total_workshops': total_workshops,
		'total_employees': total_employees,
		'total_active_tasks': total_active_tasks,
		'avg_productivity': avg_productivity,
		'total_stats': total_stats,
	}
	
	return render(request, 'workshops.html', context)

def master_dashboard(request):
    """Страница мастера с его цехами и статистикой"""
    # Проверяем, является ли пользователь мастером
    if not hasattr(request.user, 'role') or request.user.role != 'master':
        return render(request, 'workshops.html', {'error': 'Доступ только для мастеров'})
    
    # Простая проверка мобильного устройства по User-Agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    ua_lower = user_agent.lower()
    is_mobile = any(token in ua_lower for token in ['mobile', 'android', 'iphone', 'ipad'])
    
    if is_mobile:
        return render(request, 'master_dashboard_mobile.html')
    
    return render(request, 'master_dashboard.html')
