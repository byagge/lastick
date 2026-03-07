from django.db import models

# Create your models here.

class Client(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('inactive', 'Неактивный'),
        ('potential', 'Потенциальный'),
        ('blocked', 'Заблокирован'),
    ]
    
    name = models.CharField('Имя клиента', max_length=150)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    whatsapp = models.CharField('WhatsApp', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)
    company = models.CharField('Компания/Организация', max_length=150, blank=True)
    address = models.CharField('Адрес', max_length=255, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        app_label = 'clients'

    def __str__(self):
        return f"{self.name} ({self.company})" if self.company else self.name
