from celery import shared_task
from django.utils import timezone
from .models import AttendanceRecord


@shared_task
def auto_checkout_after_6pm():
    """
    Автоматически отмечает уход сотрудников после конца смены.
    """
    current_time = timezone.now()

    active_records = AttendanceRecord.objects.select_related('employee').filter(
        check_in__isnull=False,
        check_out__isnull=True
    )
    
    if not active_records.exists():
        return {
            'status': 'success',
            'message': 'Нет сотрудников для автоматической отметки ухода',
            'checked_out_count': 0
        }
    
    checked_out_count = 0
    for record in active_records:
        shift_end = record.get_shift_end()
        if shift_end and current_time >= shift_end:
            record.check_out = shift_end
            record.save()
            checked_out_count += 1
    
    return {
        'status': 'success',
        'message': f'Автоматически отмечен уход для {checked_out_count} сотрудников',
        'checked_out_count': checked_out_count,
        'checkout_time': current_time.isoformat()
    }


@shared_task
def cleanup_old_attendance_records():
    """
    Очищает старые записи посещаемости (старше 1 года)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.localdate() - timedelta(days=365)
    deleted_count = AttendanceRecord.objects.filter(date__lt=cutoff_date).delete()[0]
    
    return {
        'status': 'success',
        'message': f'Удалено {deleted_count} старых записей посещаемости',
        'deleted_count': deleted_count
    }


@shared_task
def recalculate_today_penalties():
    """
    Пересчитывает штрафы за сегодняшний день
    """
    today = timezone.localdate()
    today_records = AttendanceRecord.objects.filter(date=today)
    
    updated_count = 0
    for record in today_records:
        if record.recalculate_penalty():
            updated_count += 1
            record.save()
    
    return {
        'status': 'success',
        'message': f'Штрафы пересчитаны для {updated_count} записей',
        'updated_count': updated_count
    } 
