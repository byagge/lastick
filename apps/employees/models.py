from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

class EmployeeContactInfo(models.Model):
    """Контактная информация сотрудника"""
    employee = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='contact_info',
        verbose_name='Сотрудник'
    )
    
    # Экстренная связь
    emergency_contact = models.CharField(
        max_length=150, 
        blank=True, 
        verbose_name='Контакт для экстренной связи'
    )
    emergency_phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name='Телефон экстренной связи'
    )
    
    # Адрес
    address = models.TextField(
        blank=True, 
        verbose_name='Адрес проживания'
    )
    
    # Дополнительные контакты
    alternative_phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name='Дополнительный телефон'
    )
    skype = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Skype'
    )
    telegram = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Telegram'
    )
    
    class Meta:
        verbose_name = 'Контактная информация'
        verbose_name_plural = 'Контактная информация'
    
    def __str__(self):
        return f"Контакты {self.employee.get_full_name()}"


class EmployeeMedicalInfo(models.Model):
    """Медицинская информация сотрудника"""
    employee = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='medical_info',
        verbose_name='Сотрудник'
    )
    
    # Медосмотры
    medical_examination_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Дата медосмотра'
    )
    medical_examination_expiry = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Дата истечения медосмотра'
    )
    
    # Медицинская книжка
    medical_book_number = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name='Номер медицинской книжки'
    )
    medical_book_issue_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Дата выдачи медкнижки'
    )
    medical_book_expiry_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Дата истечения медкнижки'
    )
    
    # Дополнительная медицинская информация
    blood_type = models.CharField(
        max_length=10, 
        blank=True, 
        verbose_name='Группа крови'
    )
    allergies = models.TextField(
        blank=True, 
        verbose_name='Аллергии'
    )
    chronic_diseases = models.TextField(
        blank=True, 
        verbose_name='Хронические заболевания'
    )
    medications = models.TextField(
        blank=True, 
        verbose_name='Принимаемые лекарства'
    )
    
    class Meta:
        verbose_name = 'Медицинская информация'
        verbose_name_plural = 'Медицинская информация'
    
    def __str__(self):
        return f"Медицинская информация {self.employee.get_full_name()}"


class EmployeeStatistics(models.Model):
    """Статистика сотрудника"""
    employee = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='statistics',
        verbose_name='Сотрудник'
    )
    
    # Основные метрики
    completed_works = models.IntegerField(
        default=0, 
        verbose_name='Выполнено работ за месяц'
    )
    defects = models.IntegerField(
        default=0, 
        verbose_name='Количество браков'
    )
    monthly_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name='Заработок за месяц'
    )
    efficiency = models.IntegerField(
        default=0, 
        verbose_name='Эффективность (%)'
    )
    
    # Оклад и зарплата
    salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Оклад'
    )
    
    # Дополнительные метрики
    avg_productivity = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0, 
        verbose_name='Средняя производительность (ед./день)'
    )
    defect_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0, 
        verbose_name='Процент брака (%)'
    )
    hours_worked = models.IntegerField(
        default=0, 
        verbose_name='Отработано часов'
    )
    overtime_hours = models.IntegerField(
        default=0, 
        verbose_name='Сверхурочные часы'
    )
    
    # Качество работы
    quality_score = models.IntegerField(
        default=0, 
        verbose_name='Качество продукции (0-10)'
    )
    deadline_compliance = models.IntegerField(
        default=0, 
        verbose_name='Соблюдение сроков (%)'
    )
    initiative_score = models.IntegerField(
        default=0, 
        verbose_name='Инициативность (0-10)'
    )
    teamwork_score = models.IntegerField(
        default=0, 
        verbose_name='Командная работа (0-10)'
    )
    
    # Графики и история
    productivity_chart = models.JSONField(
        default=list, 
        verbose_name='График производительности (7 дней)'
    )
    monthly_productivity = models.JSONField(
        default=list, 
        verbose_name='Производительность за месяц (30 дней)'
    )
    salary_history = models.JSONField(
        default=list, 
        verbose_name='История заработка (6 месяцев)'
    )
    
    # Метаданные
    last_updated = models.DateTimeField(
        auto_now=True, 
        verbose_name='Последнее обновление'
    )
    
    class Meta:
        verbose_name = 'Статистика сотрудника'
        verbose_name_plural = 'Статистика сотрудников'
    
    def __str__(self):
        return f"Статистика {self.employee.get_full_name()}"


class EmployeeTask(models.Model):
    """Задачи сотрудника"""
    employee = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='tasks',
        verbose_name='Сотрудник'
    )
    text = models.TextField(verbose_name='Текст задачи')
    completed = models.BooleanField(
        default=False, 
        verbose_name='Выполнено'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Дата выполнения'
    )
    
    class Meta:
        verbose_name = 'Задача сотрудника'
        verbose_name_plural = 'Задачи сотрудников'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Задача {self.employee.get_full_name()}: {self.text[:50]}"


class EmployeeNotification(models.Model):
    """Уведомления сотрудника"""
    employee = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name='Сотрудник'
    )
    title = models.CharField(
        max_length=200, 
        verbose_name='Заголовок'
    )
    text = models.TextField(verbose_name='Текст уведомления')
    is_read = models.BooleanField(
        default=False, 
        verbose_name='Прочитано'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Уведомление сотрудника'
        verbose_name_plural = 'Уведомления сотрудников'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Уведомление {self.employee.get_full_name()}: {self.title}"


        return f"Документ {self.employee.get_full_name()}: {self.get_document_type_display()}"


# Сигналы для автоматического создания связанных записей
# Временно отключены для предотвращения конфликтов при создании через админку
# @receiver(post_save, sender=User)
# def create_employee_related_records(sender, instance, created, **kwargs):
#     """Автоматически создает связанные записи при создании пользователя"""
#     if created:
#         # Проверяем, что это сотрудник (не админ)
#         if instance.role == User.Role.WORKER:
#             try:
#                 with transaction.atomic():
#                     # Проверяем, существуют ли уже записи
#                     stats_exists = EmployeeStatistics.objects.filter(employee=instance).exists()
#                     contact_exists = EmployeeContactInfo.objects.filter(employee=instance).exists()
#                     medical_exists = EmployeeMedicalInfo.objects.filter(employee=instance).exists()
#                     
#                     # Создаем статистику только если её нет
#                     if not stats_exists:
#                         EmployeeStatistics.objects.create(employee=instance)
#                     
#                     # Создаем контактную информацию только если её нет
#                     if not contact_exists:
#                         EmployeeContactInfo.objects.create(employee=instance)
#                     
#                     # Создаем медицинскую информацию только если её нет
#                     if not medical_exists:
#                         EmployeeMedicalInfo.objects.create(employee=instance)
#                     
#                     # Создаем базовые документы только если их нет
#                     existing_docs = set(EmployeeDocument.objects.filter(
#                         employee=instance
#                     ).values_list('document_type', flat=True))
#                     
#                     basic_documents = [
#                         'passport_main',
#                         'passport_registration', 
#                         'employment_contract',
#                         'work_book',
#                         'employment_order',
#                         'medical_book'
#                     ]
#                     
#                     for doc_type in basic_documents:
#                         if doc_type not in existing_docs:
#                             EmployeeDocument.objects.create(
#                                 employee=instance,
#                                 document_type=doc_type,
#                                 status='missing'
#                             )
#                     
#             except Exception as e:
#                 # Логируем ошибку, но не прерываем создание пользователя
#                 print(f"Ошибка при создании связанных записей для пользователя {instance.id}: {e}")


@receiver(post_save, sender=User)
def save_employee_related_records(sender, instance, **kwargs):
    """Сохраняет связанные записи при обновлении пользователя"""
    # Проверяем, что это сотрудник (не админ)
    if instance.role == User.Role.WORKER:
        try:
            # Обновляем статистику если она существует
            if hasattr(instance, 'statistics'):
                instance.statistics.save()
            
            # Обновляем контактную информацию если она существует
            if hasattr(instance, 'contact_info'):
                instance.contact_info.save()
            
            # Обновляем медицинскую информацию если она существует
            if hasattr(instance, 'medical_info'):
                instance.medical_info.save()
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение пользователя
            print(f"Ошибка при сохранении связанных записей для пользователя {instance.id}: {e}")
