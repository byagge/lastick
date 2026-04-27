from django.db import models
from datetime import datetime, time, timedelta
from django.utils import timezone

# Create your models here.

class Order(models.Model):
    STATUS_CHOICES = [
        ('production', 'В производстве'),
        ('stock', 'На складе'),
        ('shipped', 'Отправлен клиенту'),
        ('new', 'Новая'),
    ]
    name = models.CharField('Название заявки', max_length=200)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='orders', verbose_name='Клиент')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Этап (цех)')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='orders', verbose_name='Продукт', null=True, blank=True)
    quantity = models.PositiveIntegerField('Количество', default=1)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    status = models.CharField('Статус', max_length=30, choices=STATUS_CHOICES, default='production')
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    # Это поле будет вычисляться в будущем (расходы на сырье, услуги, браки)
    expenses = models.FloatField('Расходы', default=0, editable=False)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        product_part = f" — {self.product} x{self.quantity}" if self.product else ""
        return f"{self.name} ({self.client}){product_part} [{self.status_display}]"

    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def total_done_count(self):
        return sum(stage.done_count for stage in self.stages.all())

    @property
    def total_defective_count(self):
        return sum(stage.defective_count for stage in self.stages.all())

    @property
    def total_quantity(self):
        """Общее количество товаров в заказе"""
        items_sum = sum(item.quantity for item in self.items.all())
        return items_sum if items_sum > 0 else (self.quantity or 0)
    
    @property
    def has_glass_items(self):
        """Проверяет, есть ли в заказе стеклянные изделия"""
        return any(item.product.is_glass for item in self.items.all() if item.product)
    
    @property
    def glass_items(self):
        """Возвращает все стеклянные позиции заказа"""
        return [item for item in self.items.all() if item.product and item.product.is_glass]
    
    @property
    def regular_items(self):
        """Возвращает все обычные (не стеклянные) позиции заказа"""
        return [item for item in self.items.all() if item.product and not item.product.is_glass]
    
    def get_order_summary(self):
        """Возвращает сводку по всему заказу"""
        summary = {
            'order_id': self.id,
            'order_name': self.name,
            'client': self.client.name if self.client else '',
            'status': self.status,
            'total_quantity': self.total_quantity,
            'has_glass_items': self.has_glass_items,
            'items': [],
            'glass_items': [],
            'regular_items': [],
        }
        
        for item in self.items.all():
            item_summary = {
                'id': item.id,
                'product': item.product.name if item.product else '',
                'quantity': item.quantity,
                'size': item.size,
                'color': item.color,
                'is_glass': item.product.is_glass if item.product else False,
                'glass_type': item.get_glass_type_display(),
                'paint_type': item.paint_type,
                'paint_color': item.paint_color,
            }
            
            summary['items'].append(item_summary)
            
            if item.product and item.product.is_glass:
                summary['glass_items'].append(item_summary)
            else:
                summary['regular_items'].append(item_summary)
        
        return summary
    
    def get_workshop_tasks(self, workshop_name):
        """Возвращает задачи для конкретного цеха с необходимой информацией"""
        tasks = []
        
        for item in self.items.all():
            if not item.product:
                continue
                
            workshop_info = item.get_workshop_info(workshop_name)
            if workshop_info:
                tasks.append({
                    'item': item,
                    'workshop_info': workshop_info,
                    'is_glass': item.product.is_glass,
                    'glass_type': item.get_glass_type_display(),
                })
        
        return tasks

class OrderStage(models.Model):
    STAGE_TYPE_CHOICES = [
        ('workshop', 'Цех'),
        ('stock', 'Склад готовой продукции'),
    ]
    STAGE_STATUS_CHOICES = [
        ('in_progress', 'В работе'),
        ('done', 'Завершено'),
        ('partial', 'Частично завершено'),
        ('waiting', 'Ожидание'),
    ]
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='stages')
    order_item = models.ForeignKey('OrderItem', on_delete=models.CASCADE, related_name='stages', null=True, blank=True, verbose_name='Позиция заказа')
    stage_type = models.CharField('Тип этапа', max_length=20, choices=STAGE_TYPE_CHOICES, default='workshop')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.CASCADE, null=True, blank=True)
    finished_good = models.ForeignKey('finished_goods.FinishedGood', on_delete=models.SET_NULL, null=True, blank=True)
    in_progress = models.PositiveIntegerField('В работе', default=0)
    defective = models.PositiveIntegerField('Брак', default=0)
    completed = models.PositiveIntegerField('Передано дальше', default=0)
    date = models.DateTimeField('Дата', auto_now=True)
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    operation = models.CharField('Операция', max_length=100, blank=True)
    sequence = models.PositiveIntegerField('Очередность', default=0)
    plan_quantity = models.PositiveIntegerField('План (кол-во)', default=1)
    completed_quantity = models.PositiveIntegerField('Выполнено (кол-во)', default=0)
    deadline = models.DateField('Срок', null=True, blank=True)
    status = models.CharField('Статус', max_length=30, choices=STAGE_STATUS_CHOICES, default='in_progress')
    parallel_group = models.PositiveIntegerField('Группа параллельной обработки', null=True, blank=True, help_text='Для параллельных потоков (например, стекло)')
    
    # Поля для спецификаций
    cnc_specs = models.TextField('Спецификации ЧПУ', blank=True, null=True)
    cutting_specs = models.TextField('Спецификации распила', blank=True, null=True)
    paint_type = models.CharField('Тип краски', max_length=100, blank=True, null=True)
    paint_color = models.CharField('Цвет краски', max_length=100, blank=True, null=True)
    
    # Поля для отслеживания времени
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        unique_together = ('order', 'workshop', 'stage_type', 'finished_good', 'order_item', 'parallel_group')
        verbose_name = 'Этап заказа'
        verbose_name_plural = 'Этапы заказа'

    def __str__(self):
        item_info = f" — {self.order_item}" if self.order_item else ""
        parallel_info = f" [Параллельная группа {self.parallel_group}]" if self.parallel_group else ""
        
        if self.stage_type == 'stock':
            return f"[Склад] {self.order}{item_info} — {self.finished_good}: {self.in_progress} на складе{parallel_info}"
        return f"{self.order}{item_info} — {self.workshop}: {self.in_progress} в работе, {self.completed} передано, {self.defective} брак{parallel_info}"

    @property
    def waiting_for_master(self):
        # Сколько ещё не распределено сотрудникам
        assigned = sum(task.quantity for task in self.employee_tasks.all())
        return max(0, self.plan_quantity - assigned)

    @property
    def in_progress_count(self):
        # Сколько назначено сотрудникам, но не выполнено
        return sum(task.quantity for task in self.employee_tasks.filter(is_completed=False))

    @property
    def done_count(self):
        # Сколько сотрудники уже выполнили (сумма completed_quantity по EmployeeTask)
        return sum(task.completed_quantity for task in self.employee_tasks.all())

    @property
    def defective_count(self):
        # Сумма брака по всем задачам этапа
        return sum(task.defective_quantity for task in self.employee_tasks.all())

    @property
    def transferred_count(self):
        # Сколько мастер перевёл на следующий цех (используем completed)
        return self.completed

    def get_workshop_info(self):
        """Возвращает информацию для цеха на основе связанной позиции заказа"""
        if self.order_item and self.order_item.product:
            return self.order_item.get_workshop_info(self.workshop.name if self.workshop else '')
        # Для агрегированного этапа (без конкретной позиции) вернем сводную информацию по всем товарам заказа
        if not self.order_item and self.order and self.order.items.exists():
            workshop_name = self.workshop.name if self.workshop else ''
            items_info = []
            total_qty = 0
            product_names = []
            
            # Если это цех ID 3 или 4, добавляем preparation_specs из всех товаров
            preparation_specs_list = []
            
            for item in self.order.items.all():
                info = item.get_workshop_info(workshop_name)
                # добавим название товара в каждую запись
                try:
                    info['product'] = item.product.name if item.product else 'Не указан'
                    product_names.append(info['product'])
                except Exception:
                    info['product'] = 'Не указан'
                total_qty += info.get('quantity', 0) or 0
                items_info.append(info)
                
                # Собираем preparation_specs для цехов ID 3 и 4
                if self.workshop and self.workshop.id in [3, 4] and item.preparation_specs:
                    preparation_specs_list.append(item.preparation_specs)
            
            result = {
                'items': items_info,
                'total_quantity': total_qty,
                'products': ', '.join(product_names),
            }
            
            # Добавляем preparation_specs для цехов ID 3 и 4
            if self.workshop and self.workshop.id in [3, 4] and preparation_specs_list:
                result['preparation_specs'] = '; '.join(preparation_specs_list)
            
            return result
        return {}
    
    def is_glass_stage(self):
        """Проверяет, относится ли этап к обработке стекла"""
        return self.parallel_group == 1
    
    def is_packaging_stage(self):
        """Проверяет, является ли этап упаковкой"""
        return 'упаковк' in (self.operation or '').lower()
    
    def can_proceed_to_packaging(self):
        """Проверяет, можно ли переходить к упаковке (для стеклянных изделий)"""
        if not self.is_glass_stage() or not self.is_packaging_stage():
            return True
        
        # Для упаковки стекла проверяем, завершена ли резка стекла
        if self.order_item:
            return self.order_item.glass_cutting_completed
        
        return True

    def confirm_stage(self, completed_qty):
        """
        Мастер подтверждает выполнение этапа. Если выполнено не всё — остаток остаётся, выполненное уходит дальше.
        """
        from apps.orders.models import OrderStage
        
        # Проверяем, можно ли переходить к упаковке (для стеклянных изделий)
        if not self.can_proceed_to_packaging():
            return False, "Нельзя переходить к упаковке: резка стекла не завершена"
        
        if completed_qty >= self.plan_quantity:
            self.completed_quantity = self.plan_quantity
            self.status = 'done'
            self.save()
            
            # Если это этап резки стекла, отмечаем его как завершенный
            if self.is_glass_stage() and 'распил стекла' in (self.operation or '').lower():
                if self.order_item:
                    self.order_item.glass_cutting_completed = True
                    self.order_item.glass_cutting_quantity = completed_qty
                    self.order_item.save()
            
            # Если это этап упаковки, создаем запись в finished_goods
            if self.is_packaging_stage():
                self._create_finished_good(completed_qty)
            
            # Специальная логика для цеха ID4 (Пресс) - завершаем заказ
            if self.workshop and self.workshop.id == 4:
                # Завершаем весь заказ
                self.order.status = 'completed'
                self.order.save()
                print(f"Заказ {self.order.id} завершен после выполнения этапа в цеху 4")
                return True, "Заказ завершен"
            
            self._activate_next_stage(self.plan_quantity)
        elif completed_qty > 0:
            # Часть выполнено, часть — остаток
            self.completed_quantity = completed_qty
            self.status = 'partial'
            self.save()
            
            # Если это этап резки стекла, отмечаем его как завершенный
            if self.is_glass_stage() and 'распил стекла' in (self.operation or '').lower():
                if self.order_item:
                    self.order_item.glass_cutting_completed = True
                    self.order_item.glass_cutting_quantity = completed_qty
                    self.order_item.save()
            
            # Если это этап упаковки, создаем запись в finished_goods
            if self.is_packaging_stage():
                self._create_finished_good(completed_qty)
            
            # Специальная логика для цеха ID4 (Пресс) - завершаем заказ даже при частичном выполнении
            if self.workshop and self.workshop.id == 4:
                # Завершаем весь заказ
                self.order.status = 'completed'
                self.order.save()
                print(f"Заказ {self.order.id} завершен после частичного выполнения этапа в цеху 4")
                return True, "Заказ завершен"
            
            self._activate_next_stage(completed_qty)
            # Создаём новый этап-остаток в этом же цехе
            OrderStage.objects.create(
                order=self.order,
                order_item=self.order_item,
                stage_type=self.stage_type,
                workshop=self.workshop,
                operation=self.operation,
                sequence=self.sequence,
                plan_quantity=self.plan_quantity - completed_qty,
                completed_quantity=0,
                deadline=None,  # Можно задать новый срок
                status='in_progress',
                parallel_group=self.parallel_group,
            )
        else:
            # Ничего не сделано — этап остаётся в работе
            pass
        
        return True, "Этап подтвержден"
    
    def _create_finished_good(self, quantity):
        """Создает запись в finished_goods при завершении упаковки"""
        if not self.order_item:
            return
        
        from apps.finished_goods.models import FinishedGood
        
        # Создаем запись о готовой продукции
        finished_good = FinishedGood.objects.create(
            product=self.order_item.product,
            order_item=self.order_item,
            order=self.order,
            quantity=quantity,
            workshop=self.workshop,
            status='stock'
        )
        
        # Отмечаем как упакованный
        finished_good.mark_as_packaged(self.workshop)

        # Пытаемся сразу рассчитать фактическую себестоимость для партии,
        # чтобы на складе была актуальная информация по труду и сырью.
        try:
            finished_good.calculate_actual_cost(save=True)
        except Exception:
            # Не блокируем основной процесс, если расчёт не удался
            pass
        
        # Обновляем количество полученное в упаковке
        self.order_item.record_packaging_receipt(quantity)

    def _activate_next_stage(self, qty):
        """
        Активирует следующий этап, если он есть, и передаёт туда qty.
        Если следующего этапа нет — создаёт его по workflow.
        """
        from apps.orders.models import OrderStage
        
        # Определяем, к какому потоку относится текущий этап
        current_parallel_group = self.parallel_group
        current_order_item = self.order_item
        
        # Ищем следующий этап в том же потоке
        next_seq = self.sequence + 1
        
        if current_parallel_group is not None:
            # Для параллельных потоков ищем следующий этап в той же группе
            next_stage = OrderStage.objects.filter(
                order=self.order,
                order_item=current_order_item,
                parallel_group=current_parallel_group,
                sequence=next_seq
            ).first()
        else:
            # Для основного потока ищем следующий этап
            next_stage = OrderStage.objects.filter(
                order=self.order,
                order_item=current_order_item,
                parallel_group__isnull=True,
                sequence=next_seq
            ).first()
        
        if next_stage:
            # Активируем существующий этап
            next_stage.plan_quantity += qty
            next_stage.status = 'in_progress'
            next_stage.save()
        else:
            # Создаем новый этап по workflow
            if current_parallel_group is not None:
                # Для параллельных потоков (стекло)
                workflow_steps = [step for step in ORDER_WORKFLOW if step.get("parallel_group") == current_parallel_group]
            else:
                # Для основного потока (обычные товары)
                workflow_steps = [step for step in ORDER_WORKFLOW if step.get("parallel_group") is None]
            
            if next_seq - 1 < len(workflow_steps):
                step = workflow_steps[next_seq - 1]
                from apps.operations.workshops.models import Workshop
                try:
                    workshop = Workshop.objects.get(pk=step["workshop"])
                    
                    OrderStage.objects.create(
                        order=self.order,
                        order_item=current_order_item,
                        sequence=next_seq,
                        stage_type='workshop',
                        workshop=workshop,
                        operation=step["operation"],
                        plan_quantity=qty,
                        deadline=timezone.now().replace(hour=18, minute=0, second=0, microsecond=0).date(),
                        status='in_progress',
                        parallel_group=current_parallel_group,
                    )
                except Workshop.DoesNotExist:
                    print(f"Workshop with ID {step['workshop']} not found, cannot create next stage")
            else:
                # Если это последний этап в workflow
                # Для стеклянного потока (parallel_group=1) — не создаём упаковку, этапы завершаются на цехе 5
                if current_parallel_group is None:
                    self._create_packaging_stage(qty)
                else:
                    return
    
    def _create_packaging_stage(self, qty):
        """
        Создает этап упаковки после завершения всех производственных этапов
        """
        from apps.orders.models import OrderStage
        from apps.operations.workshops.models import Workshop
        
        # Ищем цех упаковки (обычно это последний цех в списке)
        try:
            packaging_workshop = Workshop.objects.filter(name__icontains='упаковк').first()
            if not packaging_workshop:
                # Если не нашли цех упаковки, используем цех ID 12 (Упаковка готовой продукции)
                packaging_workshop = Workshop.objects.get(pk=12)
        except Workshop.DoesNotExist:
            print("Packaging workshop not found, skipping packaging stage creation")
            return
        
        # Создаем этап упаковки
        OrderStage.objects.create(
            order=self.order,
            order_item=self.order_item,
            sequence=self.sequence + 1,
            stage_type='workshop',
            workshop=packaging_workshop,
            operation='Упаковка готовой продукции',
            plan_quantity=qty,
            deadline=timezone.now().replace(hour=18, minute=0, second=0, microsecond=0).date(),
            status='in_progress',
            parallel_group=self.parallel_group,  # Сохраняем группу для отслеживания потока
        )

class OrderDefect(models.Model):
    DEFECT_STATUS_CHOICES = [
        ('pending_review', 'Ожидает проверки'),
        ('approved_for_rework', 'Разрешена переработка'),
        ('in_rework', 'В переработке'),
        ('reworked', 'Переработан'),
        ('rejected', 'Отклонен'),
    ]
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='order_defects')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField('Количество брака', default=1)
    date = models.DateTimeField('Дата', auto_now_add=True)
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    
    # Новые поля для управления браком
    status = models.CharField('Статус брака', max_length=30, choices=DEFECT_STATUS_CHOICES, default='pending_review')
    admin_comment = models.TextField('Комментарий админа', blank=True)
    rework_task = models.ForeignKey('employee_tasks.EmployeeTask', on_delete=models.SET_NULL, null=True, blank=True, related_name='reworked_defects')
    rework_deadline = models.DateField('Срок переработки', null=True, blank=True)
    rework_cost = models.DecimalField('Стоимость переработки', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Брак по заказу'
        verbose_name_plural = 'Браки по заказу'
        ordering = ['-date']

    def __str__(self):
        return f"Брак: {self.order} — {self.workshop} ({self.quantity}) [{self.get_status_display()}]"
    
    @property
    def status_display(self):
        return dict(self.DEFECT_STATUS_CHOICES).get(self.status, self.status)
    
    def can_be_reworked(self):
        """Проверяет, можно ли переработать брак"""
        return self.status in ['pending_review', 'approved_for_rework']
    
    def approve_for_rework(self, admin_user, comment='', deadline=None):
        """Админ разрешает переработку брака"""
        if self.status != 'pending_review':
            return False, "Брак уже не в статусе ожидания проверки"
        
        self.status = 'approved_for_rework'
        self.admin_comment = comment
        self.rework_deadline = deadline
        self.save()
        
        # Увеличиваем план первого этапа заказа, чтобы покрыть брак
        try:
            first_stage = self.order.stages.order_by('sequence').first()
            if first_stage:
                first_stage.plan_quantity = (first_stage.plan_quantity or 0) + self.quantity
                # Добавим пометку
                if first_stage.operation:
                    first_stage.operation = f"{first_stage.operation} (покрытие брака заказа #{self.order.id})"
                else:
                    first_stage.operation = f"Покрытие брака заказа #{self.order.id}"
                first_stage.save()
        except Exception:
            pass
        
        # Создаем задачу на переработку
        self._create_rework_task()
        return True, "Брак разрешен к переработке"
    
    def _create_rework_task(self):
        """Создает/обновляет этап для переработки брака (без создания задачи)"""
        # Создаем новый этап для переработки
        rework_stage, created = OrderStage.objects.get_or_create(
            order=self.order,
            workshop=self.workshop,
            stage_type='workshop',
            defaults={
                'operation': f'Переработка брака: {self.comment}',
                'plan_quantity': self.quantity,
                'status': 'in_progress',
                'deadline': self.rework_deadline,
                'sequence': 999  # Высокий приоритет
            }
        )
        
        if not created:
            rework_stage.plan_quantity = (rework_stage.plan_quantity or 0) + self.quantity
            rework_stage.save()
        
        # Привязку задачи создадим позже, когда будет назначен сотрудник
        return rework_stage
    
    def start_rework(self, employee):
        """Начинает переработку брака"""
        if self.status != 'approved_for_rework':
            return False, "Брак не разрешен к переработке"
        
        # Гарантируем наличие этапа
        rework_stage = self._create_rework_task()
        
        # Создаем задачу для переработки при первом старте
        if not self.rework_task:
            from apps.employee_tasks.models import EmployeeTask
            rework_task = EmployeeTask.objects.create(
                stage=rework_stage,
                employee=employee,
                quantity=self.quantity,
                completed_quantity=0,
                defective_quantity=0
            )
            self.rework_task = rework_task
        else:
            # Если задача уже есть — назначим сотрудника, если пуст
            self.rework_task.employee = employee
            self.rework_task.save()
        
        self.status = 'in_rework'
        self.save()
        
        return True, "Переработка начата"
    
    def complete_rework(self, completed_quantity, defective_quantity=0):
        """Завершает переработку брака"""
        if self.status != 'in_rework':
            return False, "Брак не в процессе переработки"
        
        if not self.rework_task:
            return False, "Задача на переработку не найдена"
        
        # Обновляем задачу
        self.rework_task.completed_quantity = completed_quantity
        self.rework_task.defective_quantity = defective_quantity
        self.rework_task.save()
        
        # Если переработка успешна
        if completed_quantity > 0 and defective_quantity == 0:
            self.status = 'reworked'
            self.rework_cost = self.rework_task.net_earnings
        else:
            # Если снова брак, возвращаем в ожидание
            self.status = 'pending_review'
        
        self.save()
        return True, "Переработка завершена"
    
    def reject_defect(self, admin_user, comment=''):
        """Админ отклоняет брак (списывает в убытки)"""
        if self.status != 'pending_review':
            return False, "Брак уже не в статусе ожидания проверки"
        
        self.status = 'rejected'
        self.admin_comment = comment
        self.save()
        
        return True, "Брак отклонен"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заявка')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='order_items', verbose_name='Товар')
    quantity = models.PositiveIntegerField('Количество', default=1)
    size = models.CharField('Размер', max_length=100, blank=True)
    color = models.CharField('Цвет', max_length=100, blank=True)
    
    # Дополнительные поля для передачи информации между цехами
    glass_type = models.CharField('Тип стекла', max_length=20, blank=True, help_text='Пескоструйный или УФ')
    paint_type = models.CharField('Тип краски', max_length=100, blank=True)
    paint_color = models.CharField('Цвет краски', max_length=100, blank=True)
    cnc_specs = models.TextField('Спецификации для ЧПУ', blank=True)
    cutting_specs = models.TextField('Спецификации для распила', blank=True)
    preparation_specs = models.TextField('Спецификации для цеха заготовки', blank=True, help_text='Комментарии и спецификации для цеха заготовки (ID 4)')
    packaging_notes = models.TextField('Заметки для упаковки', blank=True)
    
    # Поля для отслеживания прогресса по цехам
    glass_cutting_completed = models.BooleanField('Резка стекла завершена', default=False)
    glass_cutting_quantity = models.PositiveIntegerField('Количество порезанного стекла', default=0)
    packaging_received_quantity = models.PositiveIntegerField('Количество полученное в упаковке', default=0)

    class Meta:
        verbose_name = 'Позиция заявки'
        verbose_name_plural = 'Позиции заявки'

    def get_variant_label(self):
        """Возвращает строку варианта в формате: размер, цвет."""
        details = []
        if self.size:
            details.append(self.size)
        if self.color:
            details.append(self.color)
        return ', '.join(details)

    def get_display_name(self):
        """Название позиции вида: Товар (размер, цвет)."""
        product_name = self.product.name if self.product else 'Товар'
        variant_label = self.get_variant_label()
        return f"{product_name} ({variant_label})" if variant_label else product_name

    def __str__(self):
        try:
            details = [self.get_variant_label()] if self.get_variant_label() else []
            if self.glass_type:
                details.append(f"стекло: {self.get_glass_type_display()}")
            suffix = f" ({', '.join(details)})" if details else ''
            product_name = self.product.name if self.product else 'Не указан'
            return f"{product_name} x{self.quantity}{suffix}"
        except:
            return f"Товар x{self.quantity}"
    
    def get_workshop_info(self, workshop_name):
        """Возвращает информацию, необходимую для конкретного цеха"""
        try:
            info = {
                'size': self.size,
                'color': self.color,
                'quantity': self.quantity,
            }
            
            # Проверяем, что product существует
            if not self.product:
                return info
            
            if 'распил' in workshop_name.lower():
                info.update({
                    'cutting_specs': self.cutting_specs,
                    'size': self.size,
                })
            elif 'чпу' in workshop_name.lower():
                info.update({
                    'cnc_specs': self.cnc_specs,
                    'size': self.size,
                    'photo': self.product.img.url if self.product.img else None,
                })
            elif 'краск' in workshop_name.lower() or 'окрасочн' in workshop_name.lower():
                info.update({
                    'paint_type': self.paint_type,
                    'paint_color': self.paint_color,
                    'size': self.size,
                    'photo': self.product.img.url if self.product.img else None,
                })
            elif 'заготовк' in workshop_name.lower() or 'пресс' in workshop_name.lower() or 'заготовительн' in workshop_name.lower():
                info.update({
                    'preparation_specs': self.preparation_specs,
                    'size': self.size,
                    'color': self.color,
                    'photo': self.product.img.url if self.product.img else None,
                })
            elif 'упаковк' in workshop_name.lower():
                info.update({
                    'size': self.size,
                    'color': self.color,
                    'glass_type': self.glass_type,
                    'paint_type': self.paint_type,
                    'paint_color': self.paint_color,
                    'packaging_notes': self.packaging_notes,
                    'photo': self.product.img.url if self.product.img else None,
                })
            
            return info
        except:
            return {
                'size': self.size,
                'color': self.color,
                'quantity': self.quantity,
            }
    
    def get_glass_type_display(self):
        """Возвращает человекочитаемое название типа стекла"""
        if not self.glass_type:
            return ""
        
        try:
            glass_types = dict(self.product.GLASS_TYPES) if self.product else {}
            return glass_types.get(self.glass_type, self.glass_type)
        except:
            return self.glass_type or ""
    
    def save(self, *args, **kwargs):
        """Автоматически заполняем тип стекла при создании стеклянного изделия"""
        try:
            if self.product and self.product.is_glass and not self.glass_type:
                # По умолчанию устанавливаем пескоструйный тип
                self.glass_type = 'sandblasted'
        except:
            pass
        super().save(*args, **kwargs)
    
    def record_packaging_receipt(self, received_quantity):
        """Записывает количество товара, полученного в упаковке"""
        try:
            self.packaging_received_quantity = received_quantity
            self.save()
        except:
            pass
    
    def get_packaging_summary(self):
        """Возвращает сводку для упаковки"""
        try:
            summary = {
                'product': self.product.name if self.product else 'Не указан',
                'quantity': self.quantity,
                'size': self.size,
                'color': self.color,
                'glass_type': self.get_glass_type_display(),
                'paint_type': self.paint_type,
                'paint_color': self.paint_color,
                'packaging_notes': self.packaging_notes,
                'photo': self.product.img.url if self.product and self.product.img else None,
                'glass_cutting_completed': self.glass_cutting_completed,
                'glass_cutting_quantity': self.glass_cutting_quantity,
            }
            
            # Добавляем информацию о стекле, если это стеклянное изделие
            if self.product and self.product.is_glass:
                summary['is_glass'] = True
                summary['glass_type_code'] = self.glass_type
            
            return summary
        except:
            return {
                'product': 'Не указан',
                'quantity': self.quantity,
                'size': self.size,
                'color': self.color,
                'glass_type': '',
                'paint_type': '',
                'paint_color': '',
                'packaging_notes': '',
                'photo': None,
                'glass_cutting_completed': False,
                'glass_cutting_quantity': 0,
            }

# Словарь названий операций для каждого цеха
WORKSHOP_OPERATIONS = {
    1: "Распил",
    2: "ЧПУ",
    3: "Заготовка",
    4: "Пресс",
    5: "Кромка",
    6: "Шкурка аппарат",
    7: "Шкурка сухой",
    8: "Грутовка",
    9: "Шкурка белый",
    10: "Покраска",
    11: "Упаковка",
}

ORDER_WORKFLOW = [
    # Основной поток для обычных товаров (цех ID 1)
    {"workshop": 1, "operation": WORKSHOP_OPERATIONS[1], "sequence": 1, "parallel_group": None},
    # Параллельный поток для стеклянных товаров: 2 -> 3 -> 4 -> 5
    {"workshop": 2, "operation": WORKSHOP_OPERATIONS[2], "sequence": 1, "parallel_group": 1},
    {"workshop": 3, "operation": WORKSHOP_OPERATIONS[3], "sequence": 2, "parallel_group": 1},
    {"workshop": 4, "operation": WORKSHOP_OPERATIONS[4], "sequence": 3, "parallel_group": 1},
    {"workshop": 5, "operation": WORKSHOP_OPERATIONS[5], "sequence": 4, "parallel_group": 1},
    # Дополнительные цеха
    {"workshop": 6, "operation": WORKSHOP_OPERATIONS[6], "sequence": 5, "parallel_group": 1},
    {"workshop": 7, "operation": WORKSHOP_OPERATIONS[7], "sequence": 6, "parallel_group": 1},
    {"workshop": 8, "operation": WORKSHOP_OPERATIONS[8], "sequence": 7, "parallel_group": 1},
    {"workshop": 9, "operation": WORKSHOP_OPERATIONS[9], "sequence": 8, "parallel_group": 1},
    {"workshop": 10, "operation": WORKSHOP_OPERATIONS[10], "sequence": 9, "parallel_group": 1},
    {"workshop": 11, "operation": WORKSHOP_OPERATIONS[11], "sequence": 10, "parallel_group": 1},
]


def create_order_stages(order):
    from apps.operations.workshops.models import Workshop
    
    # Получаем все позиции заказа
    order_items = order.items.all()
    
    if not order_items.exists():
        # Если нет позиций, не создаем этапы
        print(f"Warning: No items found for order {order.id}, skipping stage creation")
        return
    
    # Определяем тип заказа: есть ли стеклянные товары
    has_glass_items = any(item.product and item.product.is_glass for item in order_items)
    
    now = timezone.now()
    deadline_dt = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if now.hour >= 18:
        deadline_dt += timedelta(days=1)
    
    # Создаем этапы для цехов ID1 и ID4 одновременно
    try:
        workshop_1 = Workshop.objects.get(pk=1)  # Цех ID 1 (Распил)
        workshop_4 = Workshop.objects.get(pk=4)  # Цех ID 4 (Пресс)
        total_qty = sum(item.quantity for item in order_items)
        
        # Определяем parallel_group в зависимости от наличия стеклянных товаров
        parallel_group = 1 if has_glass_items else None
        
        # Создаем этап в цехе 1 (Распил)
        stage_1, created_1 = OrderStage.objects.get_or_create(
            order=order,
            order_item=None,  # Агрегированный этап для всех товаров
            stage_type='workshop',
            workshop=workshop_1,
            sequence=1,
            parallel_group=parallel_group,
            defaults={
                'operation': WORKSHOP_OPERATIONS[1],
                'plan_quantity': total_qty,
                'deadline': deadline_dt.date(),
                'status': 'in_progress',
            }
        )
        
        if not created_1:
            # Обновляем плановое количество и статус
            stage_1.plan_quantity = total_qty
            stage_1.status = 'in_progress'
            stage_1.deadline = deadline_dt.date()
            stage_1.save(update_fields=['plan_quantity', 'status', 'deadline'])
        
        # Создаем этап в цехе 4 (Пресс) - для всех товаров
        stage_4, created_4 = OrderStage.objects.get_or_create(
            order=order,
            order_item=None,  # Агрегированный этап для всех товаров
            stage_type='workshop',
            workshop=workshop_4,
            sequence=1,
            parallel_group=parallel_group,
            defaults={
                'operation': WORKSHOP_OPERATIONS[4],
                'plan_quantity': total_qty,
                'deadline': deadline_dt.date(),
                'status': 'in_progress',
            }
        )
        
        if not created_4:
            # Обновляем плановое количество и статус
            stage_4.plan_quantity = total_qty
            stage_4.status = 'in_progress'
            stage_4.deadline = deadline_dt.date()
            stage_4.save(update_fields=['plan_quantity', 'status', 'deadline'])
        
        print(f"Created/updated stages for order {order.id}: {total_qty} items in workshop 1, {total_qty} items in workshop 4")
            
    except Workshop.DoesNotExist:
        print("Workshop with ID 1 or 4 not found, skipping stage creation")


def _create_stage_for_order_item(order, order_item):
    """Создает этап для конкретной позиции заказа с учетом типа товара"""
    from apps.operations.workshops.models import Workshop
    
    # Определяем цех в зависимости от типа товара
    if order_item.product and order_item.product.is_glass:
        # Для стеклянных: стартуем в цехе 2
        workshop_id = 2
        operation = WORKSHOP_OPERATIONS[2]
        parallel_group = 1
    else:
        workshop_id = 1  # Цех для обычных товаров
        operation = WORKSHOP_OPERATIONS[1]
        parallel_group = None
    
    try:
        workshop = Workshop.objects.get(pk=workshop_id)
    except Workshop.DoesNotExist:
        print(f"Workshop with ID {workshop_id} not found, skipping stage creation")
        return
    
    now = timezone.now()
    deadline_dt = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if now.hour >= 18:
        deadline_dt += timedelta(days=1)
    
    # Создаем этап для конкретной позиции заказа
    OrderStage.objects.create(
        order=order,
        order_item=order_item,  # Привязываем к конкретной позиции
        workshop=workshop,
        operation=operation,
        sequence=1,
        stage_type='workshop',
        plan_quantity=order_item.quantity,  # Количество из позиции заказа
        deadline=deadline_dt.date(),
        status='in_progress',
        parallel_group=parallel_group,
    )



from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Order)
def create_stages_on_order(sender, instance, created, **kwargs):
    if created and not instance.stages.exists():
        # Создаем этапы только если есть позиции заказа
        if instance.items.exists():
            create_order_stages(instance)