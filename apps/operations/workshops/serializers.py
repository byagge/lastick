from rest_framework import serializers
from .models import Workshop

class WorkshopSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    employees_count = serializers.SerializerMethodField()
    active_tasks = serializers.SerializerMethodField()
    defects = serializers.SerializerMethodField()
    productivity = serializers.SerializerMethodField()
    
    class Meta:
        model = Workshop
        fields = [
            'id', 'name', 'description', 'manager', 'manager_name', 
            'is_active', 'created_at', 'updated_at', 'employees_count',
            'active_tasks', 'defects', 'productivity'
        ]
    
    def get_employees_count(self, obj):
        """Подсчитывает количество сотрудников в цехе"""
        from apps.users.models import User
        return User.objects.filter(workshop=obj, role__in=['admin', 'accountant', 'worker']).count()
    
    def get_active_tasks(self, obj):
        """Подсчитывает количество активных задач в цехе"""
        from apps.employee_tasks.models import EmployeeTask
        return EmployeeTask.objects.filter(stage__workshop=obj).count()
    
    def get_defects(self, obj):
        """Подсчитывает количество браков в цехе"""
        from apps.defects.models import Defect
        return Defect.objects.filter(user__workshop=obj).count()
    
    def get_productivity(self, obj):
        """Вычисляет производительность цеха"""
        active_tasks = self.get_active_tasks(obj)
        return active_tasks * 10  # Упрощенный расчет 