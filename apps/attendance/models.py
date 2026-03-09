from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime, time, timedelta
from decimal import Decimal
import math

# Create your models here.

class AttendanceSettings(models.Model):
    """Настройки системы посещаемости (singleton)"""
    penalty_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        verbose_name='Штраф за час опоздания (сом)'
    )
    grace_period_minutes = models.IntegerField(
        default=10,
        verbose_name='Льготный период (минуты)'
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Настройки посещаемости'
        verbose_name_plural = 'Настройки посещаемости'

    def __str__(self):
        return f"Штраф: {self.penalty_per_hour} сом/час"

    @classmethod
    def get_settings(cls):
        """Получить настройки (singleton pattern)"""
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        return settings_obj

    def save(self, *args, **kwargs):
        # Ограничиваем количество записей до одной
        self.pk = 1
        super().save(*args, **kwargs)

class AttendanceRecord(models.Model):
    MAX_PENALTY_HOURS = 8
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name='Сотрудник'
    )
    date = models.DateField(
        default=timezone.localdate,
        verbose_name='Дата'
    )
    check_in = models.DateTimeField(
        verbose_name='Время прихода'
    )
    check_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время ухода'
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Комментарий'
    )
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        verbose_name='Сумма штрафа'
    )
    penalty_manual = models.BooleanField(
        default=False,
        verbose_name='Штраф задан вручную'
    )
    is_late = models.BooleanField(
        default=False,
        verbose_name='Опоздание'
    )

    class Meta:
        verbose_name = 'Запись о приходе'
        verbose_name_plural = 'Записи о приходах'
        unique_together = ('employee', 'date')
        ordering = ['-date', '-check_in']

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.date} ({self.check_in:%H:%M})"

    @staticmethod
    def resolve_shift_date(employee, check_in_dt):
        if not check_in_dt:
            return timezone.localdate()
        local_dt = timezone.localtime(check_in_dt)
        if employee and getattr(employee, 'work_schedule', None) == employee.WorkSchedule.NIGHT:
            if local_dt.time() < time(8, 0):
                return local_dt.date() - timedelta(days=1)
        return local_dt.date()

    def get_shift_start(self):
        if not self.date:
            return None
        schedule = getattr(self.employee, 'work_schedule', None)
        shift_start = time(20, 0) if schedule == self.employee.WorkSchedule.NIGHT else time(8, 0)
        naive_dt = datetime.combine(self.date, shift_start)
        return timezone.make_aware(naive_dt, timezone.get_current_timezone())

    def get_shift_end(self):
        if not self.date:
            return None
        schedule = getattr(self.employee, 'work_schedule', None)
        if schedule == self.employee.WorkSchedule.NIGHT:
            end_date = self.date + timedelta(days=1)
            shift_end = time(8, 0)
        else:
            end_date = self.date
            shift_end = time(20, 0)
        naive_dt = datetime.combine(end_date, shift_end)
        return timezone.make_aware(naive_dt, timezone.get_current_timezone())

    def get_late_hours(self):
        """Возвращает количество часов опоздания (с округлением вверх)"""
        if not self.check_in:
            return 0

        shift_start = self.get_shift_start()
        if not shift_start:
            return 0

        settings = AttendanceSettings.get_settings()
        local_check_in = timezone.localtime(self.check_in)
        grace_time = shift_start + timedelta(minutes=settings.grace_period_minutes)

        if local_check_in <= grace_time:
            return 0

        # Вычисляем разницу в часах (округление вверх)
        late_delta = local_check_in - grace_time
        late_hours = math.ceil(late_delta.total_seconds() / 3600)
        return late_hours

    def calculate_penalty(self):
        """Рассчитывает штраф за опоздание на основе времени опоздания"""
        if not self.check_in:
            self.is_late = False
            if not self.penalty_manual:
                self.penalty_amount = Decimal('0.00')
            return self.penalty_amount

        shift_start = self.get_shift_start()
        if not shift_start:
            self.is_late = False
            if not self.penalty_manual:
                self.penalty_amount = Decimal('0.00')
            return self.penalty_amount

        settings = AttendanceSettings.get_settings()
        local_check_in = timezone.localtime(self.check_in)
        grace_time = shift_start + timedelta(minutes=settings.grace_period_minutes)

        self.is_late = local_check_in > grace_time
        
        if not self.penalty_manual:
            if self.is_late:
                late_hours = self.get_late_hours()
                penalty_hours = min(late_hours, self.MAX_PENALTY_HOURS)
                self.penalty_amount = settings.penalty_per_hour * Decimal(str(penalty_hours))
            else:
                self.penalty_amount = Decimal('0.00')
        
        return self.penalty_amount

    def get_late_status(self):
        """Возвращает статус опоздания без изменения модели"""
        if not self.check_in:
            return False
        shift_start = self.get_shift_start()
        if not shift_start:
            return False
        settings = AttendanceSettings.get_settings()
        local_check_in = timezone.localtime(self.check_in)
        grace_time = shift_start + timedelta(minutes=settings.grace_period_minutes)
        return local_check_in > grace_time

    def recalculate_penalty(self):
        """Принудительно пересчитывает штраф (для существующих записей)"""
        old_penalty = self.penalty_amount
        old_is_late = self.is_late
        
        self.calculate_penalty()
        
        # Возвращаем True если что-то изменилось
        return old_penalty != self.penalty_amount or old_is_late != self.is_late

    def save(self, *args, **kwargs):
        if not self.date and self.check_in:
            self.date = timezone.localtime(self.check_in).date()
        self.calculate_penalty()
        super().save(*args, **kwargs)
