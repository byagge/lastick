from django.shortcuts import render, redirect
from apps.users.models import User
from rest_framework import viewsets, permissions, status
from .serializers import EmployeeSerializer
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import EmployeeStatistics
from django.db.models import Avg, Sum, Count
import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.operations.workshops.models import Workshop
from apps.operations.workshops.views import WorkshopSerializer
from .utils import calculate_employee_stats

MOBILE_UA_KEYWORDS = [
    'Mobile', 'Android', 'iPhone', 'iPad', 'iPod', 'Opera Mini', 'IEMobile', 'BlackBerry', 'webOS'
]

def is_mobile(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    return any(keyword in ua for keyword in MOBILE_UA_KEYWORDS)

def employees_list(request):
    # Просто отдаём employees.html, всё остальное через JS
    template = 'employees_mobile.html' if is_mobile(request) else 'employees.html'
    return render(request, template, {})

@login_required
def employees_workshop_list(request):
    template = 'employees_mobile.html' if is_mobile(request) else 'employees.html'
    return render(request, template, {'userWorkshopIds': [], 'userWorkshopList': []})

class IsAdminOrAccountant(permissions.BasePermission):
    """
    Доступ только для администраторов и бухгалтеров.
    """

    def has_permission(self, request, view):
        user = request.user
        role = getattr(user, 'role', None)
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or role in [User.Role.ADMIN, User.Role.ACCOUNTANT])
        )


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAccountant]

    def get_queryset(self):
        staff_roles = [User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.WORKER]
        return User.objects.filter(role__in=staff_roles).order_by('last_name', 'first_name')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated = serializer.validated_data
        
        # Автоматическая генерация username (id+num)
        # Username будет сгенерирован автоматически в модели User.save()
        
        # Если указан телефон, используем его для WhatsApp
        if 'phone' in validated and validated['phone'] and not validated.get('whatsapp'):
            validated['whatsapp'] = validated['phone']
        
        # Создаем пользователя
        user = serializer.save()
        
        # Генерируем username если не указан
        if not user.username:
            user.username = user.generate_username()
        
        # Устанавливаем пароль по умолчанию: +{username}+
        default_password = f"+{user.username}+"
        user.set_password(default_password)
        
        # Устанавливаем рейтинг по умолчанию
        if not user.rating:
            user.rating = 100
            user.credit = 0
        
        user.save()
        
        out = self.get_serializer(user)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        out = self.get_serializer(user)
        return Response(out.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='block')
    def block(self, request, pk=None):
        """
        Блокирует пользователя (доступно администратору и бухгалтеру).
        """
        employee = self.get_object()
        if getattr(employee, 'is_blocked', False):
            return Response(
                {'detail': 'Пользователь уже заблокирован', 'is_blocked': True},
                status=status.HTTP_200_OK,
            )
        employee.is_blocked = True
        employee.save(update_fields=['is_blocked'])
        return Response(
            {'detail': 'Пользователь заблокирован', 'is_blocked': True},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='unblock')
    def unblock(self, request, pk=None):
        """
        Разблокирует пользователя (доступно администратору и бухгалтеру).
        """
        employee = self.get_object()
        if not getattr(employee, 'is_blocked', False):
            return Response(
                {'detail': 'Пользователь не заблокирован', 'is_blocked': False},
                status=status.HTTP_200_OK,
            )
        employee.is_blocked = False
        employee.save(update_fields=['is_blocked'])
        return Response(
            {'detail': 'Пользователь разблокирован', 'is_blocked': False},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Общая статистика по всем сотрудникам"""
        queryset = self.get_queryset()
        
        # Получаем статистику из связанных моделей
        total_employees = queryset.count()
        
        # Агрегируем данные из EmployeeStatistics
        all_stats = [calculate_employee_stats(emp) for emp in queryset]
        total_completed_works = sum(s['completed_works'] for s in all_stats)
        total_defects = sum(s['defects'] for s in all_stats)
        total_salary = sum(s['monthly_salary'] for s in all_stats)
        average_efficiency = round(sum(s['efficiency'] for s in all_stats) / total_employees, 1) if total_employees else 0
        active_tasks = sum(s['active_tasks'] for s in all_stats)
        
        return Response({
            'total_employees': total_employees,
            'average_efficiency': average_efficiency,
            'total_salary': total_salary,
            'active_tasks': active_tasks,
            'total_completed_works': total_completed_works,
            'total_defects': total_defects,
        })

    @action(detail=False, methods=['get'])
    def total_stats(self, request):
        """Альтернативный endpoint для общей статистики"""
        return self.stats(request)

    @action(detail=True, methods=['get'], url_path='stats')
    def individual_stats(self, request, pk=None):
        """Статистика конкретного сотрудника"""
        try:
            employee = self.get_object()
            # Получаем существующую статистику
            stats = calculate_employee_stats(employee)
            return Response(stats)
        except User.DoesNotExist:
            return Response(
                {'error': 'Сотрудник не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employees_by_workshop(request):
    """Возвращает сотрудников по id цеха (workshop_id)"""
    workshop_id = request.GET.get('workshop_id')
    
    if not workshop_id:
        return Response({'error': 'workshop_id required'}, status=400)
    
    staff_roles = [
        User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.WORKER
    ]
    
    users = User.objects.filter(role__in=staff_roles, workshop_id=workshop_id)
    
    data = EmployeeSerializer(users, many=True).data
    
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_employee_to_workshop(request):
    """Добавляет сотрудника (по id) в цех текущего пользователя (мастера)"""
    user = request.user
    if not hasattr(user, 'workshop_id') or not user.workshop_id:
        return Response({'error': 'У пользователя не указан цех'}, status=400)
    employee_id = request.data.get('employee_id')
    if not employee_id:
        return Response({'error': 'employee_id required'}, status=400)
    try:
        employee = User.objects.get(id=employee_id)
        employee.workshop_id = user.workshop_id
        employee.save()
        return Response({'success': True, 'employee_id': employee.id})
    except User.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_workshops(request):
    """Возвращает все цеха (workshops)"""
    workshops = Workshop.objects.all().order_by('name')
    data = WorkshopSerializer(workshops, many=True).data
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_employees_by_workshop(request):
    """Возвращает всех сотрудников по id цеха (workshop_id), без фильтрации по роли"""
    workshop_id = request.GET.get('workshop_id')
    if not workshop_id:
        return Response({'error': 'workshop_id required'}, status=400)
    users = User.objects.filter(workshop_id=workshop_id)
    data = EmployeeSerializer(users, many=True).data
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_employee_password(request, employee_id):
    """Изменяет пароль сотрудника (только для администраторов)"""
    user = request.user
    if not (user.is_superuser or getattr(user, 'role', None) in [User.Role.ADMIN]):
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        employee = User.objects.get(pk=employee_id)
    except User.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    new_password = request.data.get('password')
    if not new_password:
        return Response({'error': 'Пароль не указан'}, status=status.HTTP_400_BAD_REQUEST)
    
    employee.set_password(new_password)
    employee.save()
    
    return Response({'success': True, 'message': 'Пароль успешно изменен'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
# -------- Impersonation (Admin login as employee) --------
@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, 'role', None) in [User.Role.ADMIN])
def impersonate_user(request, user_id):
    """Allows admin/superuser to log in as another user (employee/master)."""
    try:
        target_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Save original user id to allow release later
    request.session['impersonator_id'] = request.user.id
    from django.contrib.auth import login
    login(request, target_user)
    return redirect('/dashboard/')

@login_required
def release_impersonation(request):
    """Return to original admin user if impersonation session exists."""
    original_id = request.session.pop('impersonator_id', None)
    if original_id:
        from django.contrib.auth import login
        try:
            original_user = User.objects.get(pk=original_id)
            login(request, original_user)
        except User.DoesNotExist:
            pass
    return redirect('/dashboard/')


def my_workshops(request):
    """
    Возвращает только те цеха, где request.user — мастер (manager)
    """
    user = request.user
    from apps.operations.workshops.models import Workshop
    workshops = Workshop.objects.filter(manager=user).order_by('name')
    data = [
        {'id': w.id, 'name': w.name} for w in workshops
    ]
    return Response(data)
