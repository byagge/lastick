from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, F, Q, Count, Avg
from apps.employee_tasks.models import EmployeeTask
from apps.orders.models import OrderStage

def calculate_employee_stats(employee, period_days=30):
    from apps.services.models import Service
    now = timezone.now()
    period_start = now - timedelta(days=period_days)

    # Все задачи сотрудника за период
    tasks = EmployeeTask.objects.filter(
        employee=employee,
        created_at__gte=period_start
    )

    completed_works = 0
    defects = 0
    total_salary = 0
    total_penalty = 0

    for task in tasks.select_related('stage__workshop'):
        completed = task.completed_quantity or 0
        defect = task.defective_quantity or 0
        completed_works += completed
        defects += defect
        service = None
        if task.stage and task.stage.operation and task.stage.workshop:
            service = Service.objects.filter(
                name=task.stage.operation,
                workshop=task.stage.workshop
            ).first()
        if service:
            total_salary += completed * float(service.service_price)
            total_penalty += defect * float(service.defect_penalty)
        else:
            # Если услуга не найдена, можно логировать или считать по 0
            pass

    monthly_salary = total_salary - total_penalty

    # Активные задачи (не завершены полностью)
    active_tasks = EmployeeTask.objects.filter(
        employee=employee,
        completed_quantity__lt=F('quantity')
    ).count()

    # Средняя производительность (ед./день)
    days = max((now - period_start).days, 1)
    avg_productivity = round(completed_works / days, 2) if days else 0

    # Процент брака
    defect_rate = round(defects / completed_works * 100, 2) if completed_works else 0

    # Часы работы (если есть completed_at и created_at)
    hours_worked = 0
    overtime_hours = 0
    if tasks.exists():
        for t in tasks.filter(completed_quantity=F('quantity'), completed_at__isnull=False):
            delta = t.completed_at - t.created_at
            hours = delta.total_seconds() / 3600
            hours_worked += hours
            if hours > 8:
                overtime_hours += hours - 8
        hours_worked = int(hours_worked)
        overtime_hours = int(overtime_hours)

    # Качество продукции (0-10)
    if defect_rate < 5:
        quality_score = 10
    elif defect_rate < 10:
        quality_score = 8
    elif defect_rate < 20:
        quality_score = 6
    else:
        quality_score = 4

    # Соблюдение сроков (%)
    total_with_deadline = 0
    on_time = 0
    for t in tasks.filter(completed_quantity=F('quantity'), completed_at__isnull=False):
        if t.stage and t.stage.deadline:
            total_with_deadline += 1
            if t.completed_at.date() <= t.stage.deadline:
                on_time += 1
    deadline_compliance = round(on_time / total_with_deadline * 100, 2) if total_with_deadline else 0

    # Инициативность и командная работа — пока среднее
    initiative_score = 7
    teamwork_score = 7

    # График производительности (7 дней)
    productivity_chart = []
    for i in range(7):
        day_start = now - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_tasks = tasks.filter(created_at__gte=day_start.replace(hour=0, minute=0, second=0, microsecond=0),
                                created_at__lt=day_end.replace(hour=0, minute=0, second=0, microsecond=0))
        day_completed = day_tasks.aggregate(total=Sum('completed_quantity'))['total'] or 0
        productivity_chart.insert(0, day_completed)

    # Производительность за месяц (30 дней)
    monthly_productivity = []
    for i in range(30):
        day_start = now - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_tasks = tasks.filter(created_at__gte=day_start.replace(hour=0, minute=0, second=0, microsecond=0),
                                created_at__lt=day_end.replace(hour=0, minute=0, second=0, microsecond=0))
        day_completed = day_tasks.aggregate(total=Sum('completed_quantity'))['total'] or 0
        monthly_productivity.insert(0, day_completed)

    # История зарплаты (6 месяцев)
    salary_history = []
    service_cache = {}
    for i in range(6):
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        month_tasks = EmployeeTask.objects.filter(
            employee=employee,
            created_at__gte=month_start,
            created_at__lt=month_end
        ).select_related('stage__workshop')
        month_salary = 0
        month_penalty = 0
        for task in month_tasks:
            completed = task.completed_quantity or 0
            defect = task.defective_quantity or 0
            service = None
            if task.stage and task.stage.operation and task.stage.workshop:
                key = (task.stage.operation, task.stage.workshop_id)
                if key in service_cache:
                    service = service_cache[key]
                else:
                    service = Service.objects.filter(
                        name=task.stage.operation,
                        workshop=task.stage.workshop
                    ).first()
                    service_cache[key] = service
            if service:
                month_salary += completed * float(service.service_price)
                month_penalty += defect * float(service.defect_penalty)
        salary_history.insert(0, month_salary - month_penalty)

    # Эффективность
    if completed_works > 0:
        efficiency = round((completed_works - defects) / completed_works * 100)
    else:
        efficiency = 0

    return {
        'completed_works': completed_works,
        'defects': defects,
        'monthly_salary': monthly_salary,
        'efficiency': efficiency,
        'active_tasks': active_tasks,
        'avg_productivity': avg_productivity,
        'defect_rate': defect_rate,
        'hours_worked': hours_worked,
        'overtime_hours': overtime_hours,
        'quality_score': quality_score,
        'deadline_compliance': deadline_compliance,
        'initiative_score': initiative_score,
        'teamwork_score': teamwork_score,
        'productivity_chart': productivity_chart,
        'monthly_productivity': monthly_productivity,
        'salary_history': salary_history,
    } 