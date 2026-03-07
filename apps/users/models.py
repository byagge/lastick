from django.contrib.auth.models import AbstractUser
from django.db import models
import re
from decimal import Decimal

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Администратор'
        ACCOUNTANT = 'accountant', 'Бухгалтер'
        WORKER = 'worker', 'Рабочий'

    class PaymentType(models.TextChoices):
        FIXED = 'fixed', 'Фиксированная'
        VARIABLE = 'variable', 'Сдельная'

    class WorkSchedule(models.TextChoices):
        DAY = 'day', 'Дневной (8-20)'
        NIGHT = 'night', 'Ночной (20-8)'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WORKER,
        verbose_name='Роль'
    )
    phone = models.CharField(max_length=20, verbose_name='Телефон', blank=True)
    email = models.EmailField(verbose_name='Email', blank=True)  # Оставляем для совместимости, но не используем
    whatsapp = models.CharField(max_length=20, verbose_name='WhatsApp', blank=True, help_text='Номер WhatsApp')
    full_name = models.CharField(max_length=255, verbose_name='Полное имя', blank=True)
    workshop = models.ForeignKey(
        'operations_workshops.Workshop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Цех'
    )
    notes = models.TextField('Примечания', blank=True)

    # Дополнительные HR-поля (без хранения документов)
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.FIXED,
        verbose_name='Тип оплаты'
    )
    work_schedule = models.CharField(
        max_length=20,
        choices=WorkSchedule.choices,
        default=WorkSchedule.DAY,
        verbose_name='График работы'
    )
    piecework_rate = models.DecimalField(
        'Ставка за кг (сдельная)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Сколько платим за 1 кг выполненной работы для этого сотрудника'
    )
    fixed_salary = models.DecimalField(
        'Фиксированная зарплата в месяц',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Месячный оклад сотрудника при фиксированном типе оплаты'
    )

    # Поле для баланса пользователя
    balance = models.DecimalField(
        'Баланс',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Текущий баланс пользователя в сомах'
    )
    
    # Рейтинг и кредит
    rating = models.IntegerField(
        'Рейтинг',
        default=100,
        help_text='Рейтинг сотрудника (максимум 100)'
    )
    credit = models.IntegerField(
        'Кредит',
        default=0,
        help_text='Кредит сотрудника (используется для расчета рейтинга)'
    )
    

    # Системные поля
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def get_full_name(self):
        """Возвращает полное имя (ФИО)"""
        if self.full_name:
            return self.full_name
        elif self.first_name and self.last_name:
            return f"{self.last_name} {self.first_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    def add_to_balance(self, amount):
        """Пополняет баланс пользователя"""
        if isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        self.balance += amount
        self.save(update_fields=['balance'])
        return self.balance

    def subtract_from_balance(self, amount):
        """Списывает с баланса пользователя"""
        if isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        if self.balance >= amount:
            self.balance -= amount
            self.save(update_fields=['balance'])
            return self.balance
        else:
            raise ValueError("Недостаточно средств на балансе")

    def get_balance_display(self):
        """Возвращает отформатированный баланс для отображения"""
        return f"{self.balance:,.2f} сомов"

    def generate_username(self):
        """Генерирует username в формате id+num"""
        # Используем формат: id + номер (например: id1, id2, id3)
        counter = User.objects.count() + 1
        username = f"id{counter}"
        
        # Проверяем уникальность
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"id{counter}"
        
        return username
    
    def update_rating_from_credit(self):
        """Обновляет рейтинг на основе кредита"""
        # Рейтинг = 100 + кредит, но не больше 100 и не меньше 0
        new_rating = max(0, min(100, 100 + self.credit))
        self.rating = new_rating
        return new_rating
    
    def add_credit(self, amount, reason=''):
        """Добавляет кредит (может быть отрицательным для штрафа)"""
        self.credit += amount
        self.update_rating_from_credit()
        self.save(update_fields=['credit', 'rating'])
        return self.rating

    def save(self, *args, **kwargs):
        """Автоматически генерируем username при сохранении"""
        if not self.username:
            self.username = self.generate_username()
        super().save(*args, **kwargs)

    def is_workshop_manager(self):
        """
        Проверяет, является ли пользователь руководителем какого-либо цеха
        """
        return self.operation_managed_workshops.exists()

    def get_managed_workshops(self):
        """
        Возвращает список цехов, которыми управляет пользователь
        """
        return self.operation_managed_workshops.all()

    def can_be_workshop_manager(self):
        """
        Проверяет, может ли пользователь быть назначен руководителем цеха.
        Сейчас руководителем может быть только обычный сотрудник (worker).
        """
        return self.role in [self.Role.WORKER]
    
    def get_statistics(self):
        """
        Возвращает статистику сотрудника
        """
        return getattr(self, 'statistics', None)
    
    def get_tasks(self):
        """
        Возвращает задачи сотрудника
        """
        return self.tasks.all()
    
    def get_notifications(self):
        """
        Возвращает уведомления сотрудника
        """
        return self.notifications.all()
    
    def get_documents(self):
        """
        Возвращает документы сотрудника
        """
        return self.documents.all()
    
    def get_contact_info(self):
        """
        Возвращает контактную информацию сотрудника
        """
        return getattr(self, 'contact_info', None)
    
    def get_medical_info(self):
        """
        Возвращает медицинскую информацию сотрудника
        """
        return getattr(self, 'medical_info', None)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

class UserSettings(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    pin_login = models.BooleanField(default=False)
    face_id = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.user_id}"
