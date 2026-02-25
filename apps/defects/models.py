from django.db import models
from apps.products.models import Product
from apps.users.models import User
from apps.operations.workshops.models import Workshop

class Defect(models.Model):
    class DefectType(models.TextChoices):
        TECHNICAL = 'technical', 'Технический'
        MANUAL = 'manual', 'Ручной'
    
    class DefectStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает подтверждения мастера'
        CONFIRMED = 'confirmed', 'Подтвержден мастером'
        REPAIRABLE = 'repairable', 'Можно починить'
        IRREPARABLE = 'irreparable', 'Нельзя починить'
        TRANSFERRED = 'transferred', 'Переведен в другой цех'
        REPAIRED = 'repaired', 'Починен'
        CLOSED = 'closed', 'Закрыт'
    
    # Связь с задачей сотрудника
    employee_task = models.ForeignKey(
        'employee_tasks.EmployeeTask',
        on_delete=models.CASCADE,
        related_name='defects',
        verbose_name='Задача сотрудника',
        null=True,
        blank=True
    )
    
    # Основная информация
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='defects', verbose_name='Продукт', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='defects', verbose_name='Сотрудник (кто создал брак)')
    created_at = models.DateTimeField('Дата брака', auto_now_add=True)
    
    # Статус и тип брака
    status = models.CharField(
        max_length=20,
        choices=DefectStatus.choices,
        default=DefectStatus.PENDING,
        verbose_name='Статус брака'
    )
    defect_type = models.CharField(
        max_length=20,
        choices=DefectType.choices,
        null=True,
        blank=True,
        verbose_name='Тип брака'
    )
    
    # Поля для подтверждения мастером или администратором
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_defects',
        verbose_name='Пользователь, подтвердивший брак'
    )
    confirmed_at = models.DateTimeField('Дата подтверждения', null=True, blank=True)
    
    # Поля для перевода в другой цех
    target_workshop = models.ForeignKey(
        Workshop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_defects',
        verbose_name='Цех для исправления'
    )
    transferred_at = models.DateTimeField('Дата перевода', null=True, blank=True)
    
    # Поля для починки
    is_repairable = models.BooleanField('Можно починить', null=True, blank=True)
    repair_task = models.ForeignKey(
        'employee_tasks.EmployeeTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='defect_repair_tasks',
        verbose_name='Задача на починку'
    )
    
    # Комментарии
    master_comment = models.TextField('Комментарий подтверждающего', blank=True)
    repair_comment = models.TextField('Комментарий по починке', blank=True)
    
    # Штрафные санкции (теперь применяются только после подтверждения мастером или администратором)
    penalty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Сумма штрафа',
    )
    penalty_applied = models.BooleanField('Штраф применен', default=False)

    def __str__(self):
        return f"Брак: {self.product} ({self.user}) - {self.get_status_display()}"

    def get_workshop(self):
        """Возвращает цех, в котором работает сотрудник, создавший брак"""
        return self.user.workshop if self.user else None
    
    def can_be_confirmed_by(self, user):
        """???????? ???? ?? ????????????? ?????."""
        if not user:
            return False
        return user.role == User.Role.ADMIN

    def confirm_defect(self, master, is_repairable, defect_type=None, target_workshop=None, comment='', penalty_amount=None):
        """Подтверждает брак мастером или администратором"""
        from django.utils import timezone
        
        if not self.can_be_confirmed_by(master):
            raise ValueError("Пользователь не может подтвердить этот брак")
        
        self.confirmed_by = master
        self.confirmed_at = timezone.now()
        self.is_repairable = is_repairable
        self.master_comment = comment
        
        # Базовый статус подтверждения
        self.status = self.DefectStatus.CONFIRMED
        
        if is_repairable:
            # Если можно починить — переводим в REPAIRABLE
            self.status = self.DefectStatus.REPAIRABLE
        else:
            # Если нельзя починить — ставим статус IRREPARABLE и тип брака
            self.status = self.DefectStatus.IRREPARABLE
            self.defect_type = defect_type
            
            # Применяем штраф только для ручного брака
            if defect_type == self.DefectType.MANUAL:
                self._apply_penalty(amount=penalty_amount)
            
            # Если указан целевой цех — переводим брак
            if target_workshop:
                self._transfer_to_workshop(target_workshop)
        
        self.save()
    
    def _apply_penalty(self, amount=None):
        """Применяет штраф за ручной брак к задаче сотрудника после подтверждения"""
        if self.user and self.user.workshop and self.employee_task:
            from apps.services.models import Service
            try:
                if amount is not None:
                    self.penalty_amount = amount
                else:
                    service = Service.objects.filter(workshop=self.user.workshop, is_active=True).first()
                    if service and hasattr(service, 'defect_penalty'):
                        self.penalty_amount = service.defect_penalty
                self.penalty_applied = True
                
                # Накопительно увеличиваем дополнительные штрафы, затем пересчитываем чистый заработок
                task = self.employee_task
                task.additional_penalties = (task.additional_penalties or 0) + self.penalty_amount
                task.calculate_earnings()
                task.save(update_fields=['earnings', 'penalties', 'net_earnings', 'additional_penalties'])
            except Exception as e:
                print(f"Ошибка при применении штрафа: {e}")
    
    def _transfer_to_workshop(self, target_workshop):
        """Переводит брак в другой цех для исправления"""
        from django.utils import timezone
        
        self.target_workshop = target_workshop
        self.transferred_at = timezone.now()
        self.status = self.DefectStatus.TRANSFERRED
        self.save()
    
    def mark_as_repaired(self, comment=''):
        """Отмечает брак как починенный"""
        from django.utils import timezone
        
        self.status = self.DefectStatus.REPAIRED
        self.repair_comment = comment
        self.save()
    
    def close_defect(self):
        """Закрывает брак"""
        self.status = self.DefectStatus.CLOSED
        self.save()

    class Meta:
        verbose_name = 'Брак'
        verbose_name_plural = 'Браки'
        ordering = ['-created_at'] 