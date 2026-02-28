from rest_framework import serializers
from apps.users.models import User
from django.utils import timezone
from .utils import calculate_employee_stats
from django.db.models import Sum
from apps.employee_tasks.models import EmployeeTask

class EmployeeSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    work_schedule_display = serializers.CharField(source='get_work_schedule_display', read_only=True)
    workshop_name = serializers.CharField(source='workshop.name', read_only=True)
    pay_category_display = serializers.CharField(source='get_pay_category_display', read_only=True)
    
    # Для фронта:
    name = serializers.CharField(source='get_full_name', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    position = serializers.CharField(source='role')
    status = serializers.SerializerMethodField()
    notes = serializers.CharField(required=False, allow_blank=True)
    payment_type = serializers.CharField(required=False)
    work_schedule = serializers.CharField(required=False)
    pay_category = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    # Баланс
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    # Статистика (из связанной модели)
    salary = serializers.SerializerMethodField()
    completed_works = serializers.SerializerMethodField()
    defects = serializers.SerializerMethodField()
    efficiency = serializers.SerializerMethodField()
    monthly_salary = serializers.SerializerMethodField()
    
    # Задачи (из связанной модели)
    tasks = serializers.SerializerMethodField()
    
    # Уведомления (из связанной модели)
    notifications = serializers.SerializerMethodField()
    
    # Документы (из связанной модели)

    class Meta:
        model = User
        fields = [
            'id', 'username',
            'first_name', 'last_name', 'name', 'full_name',
            'position', 'role', 'role_display', 'is_active', 'status',
            'phone', 'email',
            'workshop', 'workshop_name',
            'notes',
            # HR-поля (без документов)
            'payment_type', 'payment_type_display',
            'work_schedule', 'work_schedule_display',
            'pay_category', 'pay_category_display',
            # Финансы
            'balance', 'piecework_rate', 'fixed_salary',
            # Статистика
            'salary', 'completed_works', 'defects', 'efficiency', 'monthly_salary',
            # Связанные данные
            'tasks', 'notifications',
        ]

    def get_status(self, obj):
        return 'active' if obj.is_active else 'inactive'
    
    def _calc_stats(self, obj):
        try:
            return calculate_employee_stats(obj)
        except Exception:
            return {
                'completed_works': 0,
                'defects': 0,
                'monthly_salary': 0,
                'efficiency': 0,
            }
    
    def get_salary(self, obj):
        """Получить оклад из статистики"""
        if hasattr(obj, 'statistics') and obj.statistics:
            return float(obj.statistics.salary) if obj.statistics.salary else 0
        return 0
    
    def _get_or_compute_stats(self, obj):
        # Кэшируем вычисленные значения на объекте, чтобы не пересчитывать несколько раз
        cached = getattr(obj, '_computed_employee_stats', None)
        if cached is not None:
            return cached
        stats = calculate_employee_stats(obj)
        setattr(obj, '_computed_employee_stats', stats)
        return stats

    def _get_task_aggregates(self, obj):
        """Агрегации по задачам сотрудника как на странице stats_employee.html"""
        cached = getattr(obj, '_task_aggregates', None)
        if cached is not None:
            return cached
        agg = EmployeeTask.objects.filter(employee=obj).aggregate(
            total_defects=Sum('defective_quantity'),
            total_net=Sum('net_earnings'),
        )
        # Нормализуем None в 0
        agg = {
            'total_defects': agg.get('total_defects') or 0,
            'total_net': agg.get('total_net') or 0,
        }
        setattr(obj, '_task_aggregates', agg)
        return agg

    def get_completed_works(self, obj):
        """Получить количество выполненных работ"""
        if hasattr(obj, 'statistics') and obj.statistics and (obj.statistics.completed_works or 0) > 0:
            return obj.statistics.completed_works
        return self._get_or_compute_stats(obj).get('completed_works', 0)
    
    def get_defects(self, obj):
        """Получить количество браков"""
        # Приоритет: реальные данные по задачам, как на stats_employee.html
        task_agg = self._get_task_aggregates(obj)
        if (task_agg.get('total_defects') or 0) > 0:
            return int(task_agg.get('total_defects') or 0)
        if hasattr(obj, 'statistics') and obj.statistics and (obj.statistics.defects or 0) > 0:
            return obj.statistics.defects
        return int(self._get_or_compute_stats(obj).get('defects', 0))
    
    def get_efficiency(self, obj):
        """Получить эффективность"""
        if hasattr(obj, 'statistics') and obj.statistics and (obj.statistics.efficiency or 0) > 0:
            return obj.statistics.efficiency
        return self._get_or_compute_stats(obj).get('efficiency', 0)
    
    def get_monthly_salary(self, obj):
        """Получить заработок за месяц"""
        # Приоритет: сумма net_earnings по задачам (как на stats_employee.html -> total_net_earnings)
        task_agg = self._get_task_aggregates(obj)
        if (task_agg.get('total_net') or 0) != 0:
            return float(task_agg.get('total_net') or 0)
        if hasattr(obj, 'statistics') and obj.statistics and (obj.statistics.monthly_salary or 0) > 0:
            return float(obj.statistics.monthly_salary) if obj.statistics.monthly_salary else 0
        return float(self._get_or_compute_stats(obj).get('monthly_salary', 0))
    
    def get_tasks(self, obj):
        """Получить задачи сотрудника"""
        tasks = obj.tasks.all()[:10]  # Ограничиваем до 10 последних задач
        return [
            {
                'id': task.id,
                'text': task.text,
                'completed': task.completed,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            }
            for task in tasks
        ]
    
    def get_notifications(self, obj):
        """Получить уведомления сотрудника"""
        notifications = obj.notifications.all()[:5]  # Ограничиваем до 5 последних уведомлений
        return [
            {
                'id': notification.id,
                'title': notification.title,
                'text': notification.text,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat() if notification.created_at else None
            }
            for notification in notifications
        ]
    def create(self, validated_data):
        # Обработка вложенных полей / алиасов
        validated_data['role'] = validated_data.get('role') or validated_data.get('position') or User.Role.WORKER
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['role'] = validated_data.get('role') or validated_data.get('position') or instance.role
        return super().update(instance, validated_data)