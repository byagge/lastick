from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone

User = get_user_model()

# Категории расходов
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Родительская категория")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Категория расходов"
        verbose_name_plural = "Категории расходов"
        ordering = ['name']
    
    def __str__(self):
        return self.name

# Поставщики
class Supplier(models.Model):
    CATEGORY_CHOICES = [
        ('materials', 'Материалы'),
        ('services', 'Услуги'),
        ('equipment', 'Оборудование'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название поставщика")
    code = models.CharField(max_length=50, blank=True, verbose_name="Код поставщика")
    description = models.TextField(blank=True, verbose_name="Описание")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name="Категория")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="Контактное лицо")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Адрес")
    inn = models.CharField(max_length=12, blank=True, verbose_name="ИНН")
    bank_details = models.TextField(blank=True, verbose_name="Банковские реквизиты")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ['name']
    
    def __str__(self):
        return self.name

# Товары/услуги поставщиков
class SupplierItem(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Поставщик")
    name = models.CharField(max_length=200, verbose_name="Название товара/услуги")
    description = models.TextField(blank=True, verbose_name="Описание")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Цена за единицу (сом)")
    unit = models.CharField(max_length=50, verbose_name="Единица измерения")
    purchase_frequency = models.IntegerField(verbose_name="Частота покупок (дней)", default=30)
    last_purchase_date = models.DateField(null=True, blank=True, verbose_name="Дата последней покупки")
    next_purchase_date = models.DateField(null=True, blank=True, verbose_name="Дата следующей покупки")
    warehouse_connection = models.CharField(max_length=200, blank=True, verbose_name="Связь со складом")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Товар поставщика"
        verbose_name_plural = "Товары поставщиков"
        ordering = ['supplier', 'name']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.name}"

# Основной банковский счет (единственный)
class MainBankAccount(models.Model):
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Баланс (сом)")
    currency = models.CharField(max_length=3, default="KGS", verbose_name="Валюта")
    description = models.TextField(blank=True, verbose_name="Описание")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Основной банковский счет"
        verbose_name_plural = "Основной банковский счет"
    
    def __str__(self):
        return f"Основной счет - {self.balance} {self.currency}"
    
    @classmethod
    def get_main_account(cls):
        """Получить основной счет, создав его если не существует"""
        account, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'balance': Decimal('0.00'),
                'currency': 'KGS',
                'description': 'Основной банковский счет предприятия'
            }
        )
        return account

# Движение денег
class MoneyMovement(models.Model):
    MOVEMENT_TYPES = [
        ('deposit', 'Вложение'),
        ('withdrawal', 'Инкассация'),
    ]
    
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name="Тип движения")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма (сом)")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    
    class Meta:
        verbose_name = "Движение денег"
        verbose_name_plural = "Движение денег"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.amount} сом - {self.date.strftime('%d.%m.%Y')}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Только при создании
            account = MainBankAccount.get_main_account()
            if self.movement_type == 'deposit':
                account.balance += self.amount
            else:
                account.balance -= self.amount
            account.save()
        super().save(*args, **kwargs)

# Расходы
class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name="Категория")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма (сом)")
    description = models.TextField(verbose_name="Описание")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Поставщик")
    date = models.DateField(verbose_name="Дата расхода")
    invoice_number = models.CharField(max_length=100, blank=True, verbose_name="Номер счета")
    payment_method = models.CharField(max_length=50, blank=True, verbose_name="Способ оплаты")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Расход"
        verbose_name_plural = "Расходы"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.category.name} - {self.amount} сом - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Только при создании
            account = MainBankAccount.get_main_account()
            account.balance -= self.amount  # Расход уменьшает баланс
            account.save()
        super().save(*args, **kwargs)

# Доходы
class Income(models.Model):
    INCOME_TYPES = [
        ('sales', 'С продаж'),
        ('other', 'Другое'),
    ]
    
    income_type = models.CharField(max_length=20, choices=INCOME_TYPES, verbose_name="Тип дохода")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма (сом)")
    description = models.TextField(verbose_name="Описание")
    order_reference = models.CharField(max_length=100, blank=True, verbose_name="Ссылка на заказ")
    date = models.DateField(verbose_name="Дата дохода")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Доход"
        verbose_name_plural = "Доходы"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.get_income_type_display()} - {self.amount} сом - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Только при создании
            account = MainBankAccount.get_main_account()
            account.balance += self.amount  # Доход увеличивает баланс
            account.save()
        super().save(*args, **kwargs)

# Система долгов
class Debt(models.Model):
    DIRECTION_CHOICES = [
        ('payable', 'Мы должны (поставщикам)') ,
        ('receivable', 'Нам должны (клиенты)') ,
    ]

    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, verbose_name="Направление")
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='debts', verbose_name="Клиент")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Поставщик")
    counterparty_name = models.CharField(max_length=200, blank=True, verbose_name="Контрагент (если не поставщик)")
    title = models.CharField(max_length=200, verbose_name="Назначение долга")
    description = models.TextField(blank=True, verbose_name="Описание")
    original_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Сумма долга")
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), verbose_name="Оплачено")
    due_date = models.DateField(null=True, blank=True, verbose_name="Срок оплаты")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Долг"
        verbose_name_plural = "Долги"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.original_amount} сом"

    @property
    def outstanding_amount(self) -> Decimal:
        return (self.original_amount or Decimal('0.00')) - (self.amount_paid or Decimal('0.00'))

    @property
    def status(self) -> str:
        if self.amount_paid >= self.original_amount:
            return 'closed'
        if self.amount_paid > 0:
            return 'partial'
        return 'open'


class DebtPayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payments', verbose_name="Долг")
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name="Сумма оплаты")
    date = models.DateField(verbose_name="Дата оплаты")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Оплата долга"
        verbose_name_plural = "Оплаты долгов"
        ordering = ['-date', '-id']

    def __str__(self):
        return f"Оплата {self.amount} сом по: {self.debt.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Обновляем сумму оплат по долгу
            Debt.objects.filter(pk=self.debt_id).update(amount_paid=models.F('amount_paid') + self.amount)
            # Двигаем баланс основного счета
            account = MainBankAccount.get_main_account()
            if self.debt.direction == 'payable':
                # Платим поставщику -> уменьшаем баланс
                account.balance -= self.amount
            else:
                # Получили оплату от клиента -> увеличиваем баланс
                account.balance += self.amount
            account.save()

# Состояние имущества завода
class FactoryAsset(models.Model):
    ASSET_TYPES = [
        ('building', 'Здание'),
        ('equipment', 'Оборудование'),
        ('vehicle', 'Транспорт'),
        ('furniture', 'Мебель'),
        ('electronics', 'Электроника'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название")
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES, verbose_name="Тип имущества")
    description = models.TextField(blank=True, verbose_name="Описание")
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Цена покупки (сом)")
    current_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Текущая стоимость (сом)")
    purchase_date = models.DateField(verbose_name="Дата покупки")
    location = models.CharField(max_length=200, blank=True, verbose_name="Местоположение")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Поставщик")
    warranty_expiry = models.DateField(null=True, blank=True, verbose_name="Дата окончания гарантии")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Имущество завода"
        verbose_name_plural = "Имущество завода"
        ordering = ['asset_type', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.current_value} сом"

# Финансовые отчеты
class FinancialReport(models.Model):
    REPORT_TYPES = [
        ('monthly', 'Месячный'),
        ('quarterly', 'Квартальный'),
        ('yearly', 'Годовой'),
        ('custom', 'Произвольный'),
    ]
    
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name="Тип отчета")
    title = models.CharField(max_length=200, verbose_name="Название отчета")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Общий доход")
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Общий расход")
    net_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Чистый доход")
    operating_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Операционный доход")
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Общая стоимость активов")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Финансовый отчет"
        verbose_name_plural = "Финансовые отчеты"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"
    
    def calculate_totals(self):
        """Расчет всех показателей отчета"""
        # Доходы за период
        incomes = Income.objects.filter(date__range=[self.start_date, self.end_date])
        self.total_income = sum(income.amount for income in incomes)
        
        # Расходы за период
        expenses = Expense.objects.filter(date__range=[self.start_date, self.end_date])
        self.total_expenses = sum(expense.amount for expense in expenses)
        
        # Чистый доход
        self.net_income = self.total_income - self.total_expenses
        
        # Операционный доход (доходы от продаж минус расходы)
        sales_income = sum(income.amount for income in incomes if income.income_type == 'sales')
        self.operating_income = sales_income - self.total_expenses
        
        # Общая стоимость активов
        assets = FactoryAsset.objects.filter(is_active=True)
        self.total_assets = sum(asset.current_value for asset in assets)
        
        self.save()


# ====== ДВОЙНАЯ ЗАПИСЬ (ДЕБЕТ/КРЕДИТ), ПЛАН СЧЕТОВ, ЖУРНАЛ ======

class AccountingAccount(models.Model):
    """Счет бухгалтерского учета (план счетов 1С-подобный)."""
    ASSET = 'asset'
    LIABILITY = 'liability'
    EQUITY = 'equity'
    INCOME = 'income'
    EXPENSE = 'expense'
    ACCOUNT_TYPES = [
        (ASSET, 'Актив'),
        (LIABILITY, 'Пассив'),
        (EQUITY, 'Капитал'),
        (INCOME, 'Доход'),
        (EXPENSE, 'Расход'),
    ]

    DEBIT = 'debit'
    CREDIT = 'credit'
    NORMAL_SIDE_CHOICES = [
        (DEBIT, 'Дебет'),
        (CREDIT, 'Кредит'),
    ]

    code = models.CharField(max_length=20, unique=True, verbose_name="Код счета")
    name = models.CharField(max_length=200, verbose_name="Наименование счета")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, verbose_name="Тип (Актив/Пассив/…)")
    normal_side = models.CharField(max_length=6, choices=NORMAL_SIDE_CHOICES, verbose_name="Нормальная сторона")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children', verbose_name="Родительский счет")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Счет учета"
        verbose_name_plural = "План счетов"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} {self.name}"

    def get_balance(self, date_from=None, date_to=None):
        """Возвращает обороты и сальдо по счету за период."""
        from django.db.models import Sum
        lines = JournalEntryLine.objects.filter(account=self)
        if date_from:
            lines = lines.filter(entry__date__gte=date_from)
        if date_to:
            lines = lines.filter(entry__date__lte=date_to)
        agg = lines.aggregate(d=Sum('debit'), c=Sum('credit'))
        debit = agg['d'] or Decimal('0.00')
        credit = agg['c'] or Decimal('0.00')
        if self.normal_side == self.DEBIT:
            closing = debit - credit
        else:
            closing = credit - debit
        return {
            'debit_turnover': debit,
            'credit_turnover': credit,
            'closing_balance': closing,
        }


class JournalEntry(models.Model):
    """Хозяйственная операция (проводка), объединяющая строки Дт/Кт."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(verbose_name="Дата")
    memo = models.CharField(max_length=255, blank=True, verbose_name="Описание")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    posted = models.BooleanField(default=True, verbose_name="Проведено")

    class Meta:
        verbose_name = "Журнал операции"
        verbose_name_plural = "Журнал операций"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Операция {self.date} ({self.pk})"

    def total_debit(self):
        return self.lines.aggregate(s=models.Sum('debit'))['s'] or Decimal('0.00')

    def total_credit(self):
        return self.lines.aggregate(s=models.Sum('credit'))['s'] or Decimal('0.00')


class JournalEntryLine(models.Model):
    """Строка проводки: дебет/кредит конкретного счета."""
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines', verbose_name="Операция")
    account = models.ForeignKey(AccountingAccount, on_delete=models.PROTECT, verbose_name="Счет")
    analytical_account = models.ForeignKey('AnalyticalAccount', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аналитический счет")
    description = models.CharField(max_length=255, blank=True, verbose_name="Описание")
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))], verbose_name="Дебет")
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))], verbose_name="Кредит")

    class Meta:
        verbose_name = "Строка проводки"
        verbose_name_plural = "Строки проводок"

    def __str__(self):
        return f"{self.account.code}: Дт {self.debit} Кт {self.credit}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if (self.debit and self.debit > 0) and (self.credit and self.credit > 0):
            raise ValidationError("Нельзя указывать одновременно дебет и кредит в одной строке")
        if (not self.debit or self.debit == 0) and (not self.credit or self.credit == 0):
            raise ValidationError("Нужно заполнить дебет или кредит")


def create_simple_entry(date, debit_account: AccountingAccount, credit_account: AccountingAccount, amount: Decimal, memo: str = "", user=None) -> JournalEntry:
    """Утилита для быстрого создания простой проводки Дт/Кт одной суммой."""
    entry = JournalEntry.objects.create(date=date, memo=memo, created_by=user, posted=True)
    JournalEntryLine.objects.create(entry=entry, account=debit_account, debit=amount, credit=Decimal('0.00'), description=memo)
    JournalEntryLine.objects.create(entry=entry, account=credit_account, debit=Decimal('0.00'), credit=amount, description=memo)
    return entry


# ====== РАСШИРЕННАЯ БУХГАЛТЕРИЯ ======

class AnalyticalAccount(models.Model):
    """Аналитические счета для детализации синтетических счетов."""
    parent_account = models.ForeignKey(AccountingAccount, on_delete=models.CASCADE, related_name='analytical_accounts', verbose_name="Синтетический счет")
    code = models.CharField(max_length=50, verbose_name="Код аналитического счета")
    name = models.CharField(max_length=200, verbose_name="Наименование")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Аналитический счет"
        verbose_name_plural = "Аналитические счета"
        unique_together = ['parent_account', 'code']
        ordering = ['parent_account', 'code']
    
    def __str__(self):
        return f"{self.parent_account.code}.{self.code} {self.name}"
    
    def get_balance(self, date_from=None, date_to=None):
        """Возвращает обороты и сальдо по аналитическому счету."""
        from django.db.models import Sum
        lines = JournalEntryLine.objects.filter(
            account=self.parent_account,
            analytical_account=self
        )
        if date_from:
            lines = lines.filter(entry__date__gte=date_from)
        if date_to:
            lines = lines.filter(entry__date__lte=date_to)
        
        agg = lines.aggregate(d=Sum('debit'), c=Sum('credit'))
        debit = agg['d'] or Decimal('0.00')
        credit = agg['c'] or Decimal('0.00')
        
        if self.parent_account.normal_side == self.parent_account.DEBIT:
            closing = debit - credit
        else:
            closing = credit - debit
            
        return {
            'debit_turnover': debit,
            'credit_turnover': credit,
            'closing_balance': closing,
        }


class StandardOperation(models.Model):
    """Типовые хозяйственные операции для быстрого создания проводок."""
    name = models.CharField(max_length=200, verbose_name="Название операции")
    description = models.TextField(blank=True, verbose_name="Описание")
    category = models.CharField(max_length=100, blank=True, verbose_name="Категория")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Типовая операция"
        verbose_name_plural = "Типовые операции"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"


class StandardOperationLine(models.Model):
    """Строка типовой операции."""
    operation = models.ForeignKey(StandardOperation, on_delete=models.CASCADE, related_name='lines', verbose_name="Операция")
    account = models.ForeignKey(AccountingAccount, on_delete=models.CASCADE, verbose_name="Счет")
    analytical_account = models.ForeignKey('AnalyticalAccount', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аналитический счет")
    description = models.CharField(max_length=255, blank=True, verbose_name="Описание")
    debit_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Процент по дебету")
    credit_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Процент по кредиту")
    is_variable = models.BooleanField(default=False, verbose_name="Переменная сумма")
    
    class Meta:
        verbose_name = "Строка типовой операции"
        verbose_name_plural = "Строки типовых операций"
    
    def __str__(self):
        return f"{self.operation.name}: {self.account.code}"


class AccountCorrespondence(models.Model):
    """Корреспонденции счетов для проверки правильности проводок."""
    debit_account = models.ForeignKey(AccountingAccount, on_delete=models.CASCADE, related_name='debit_correspondences', verbose_name="Счет по дебету")
    credit_account = models.ForeignKey(AccountingAccount, on_delete=models.CASCADE, related_name='credit_correspondences', verbose_name="Счет по кредиту")
    description = models.CharField(max_length=255, verbose_name="Описание корреспонденции")
    is_valid = models.BooleanField(default=True, verbose_name="Корректна")
    warning_message = models.TextField(blank=True, verbose_name="Предупреждение")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Корреспонденция счетов"
        verbose_name_plural = "Корреспонденции счетов"
        unique_together = ['debit_account', 'credit_account']
        ordering = ['debit_account', 'credit_account']
    
    def __str__(self):
        return f"{self.debit_account.code} ↔ {self.credit_account.code}"


class FinancialPeriod(models.Model):
    """Финансовые периоды для закрытия счетов."""
    PERIOD_TYPES = [
        ('month', 'Месяц'),
        ('quarter', 'Квартал'),
        ('year', 'Год'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Название периода")
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES, verbose_name="Тип периода")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    is_closed = models.BooleanField(default=False, verbose_name="Закрыт")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата закрытия")
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Закрыл")
    
    class Meta:
        verbose_name = "Финансовый период"
        verbose_name_plural = "Финансовые периоды"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    def close_period(self, user):
        """Закрытие финансового периода."""
        if not self.is_closed:
            self.is_closed = True
            self.closed_at = timezone.now()
            self.closed_by = user
            self.save()
    
    def get_period_entries(self):
        """Получение всех операций за период."""
        return JournalEntry.objects.filter(
            date__range=[self.start_date, self.end_date],
            posted=True
        )

class Request(models.Model):
    """Модель для заявок от бухгалтера к администратору"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
        ('in_production', 'В производстве'),
    ]
    
    name = models.CharField('Название заявки', max_length=200)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='requests', verbose_name='Клиент')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    status = models.CharField('Статус', max_length=30, choices=STATUS_CHOICES, default='pending')
    comment = models.TextField('Комментарий', blank=True)
    total_amount = models.DecimalField('Общая сумма', max_digits=12, decimal_places=2, default=0)
    
    # Связь с заказом (создается после одобрения администратором)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_request', verbose_name='Связанный заказ')
    
    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.client}) [{self.get_status_display()}]"
    
    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def approve_and_create_order(self, admin_user):
        """Одобряет заявку и создает заказ"""
        from apps.orders.models import Order, OrderItem, create_order_stages
        
        if self.status != 'pending':
            return False, "Заявка уже не в статусе ожидания"
        
        # Создаем заказ
        order = Order.objects.create(
            name=self.name,
            client=self.client,
            status='production',
            comment=self.comment
        )
        
        # Создаем позиции заказа из заявки
        for item in self.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                size=item.size,
                color=item.color,
                glass_type=item.glass_type,
                paint_type=item.paint_type,
                paint_color=item.paint_color,
                cnc_specs=item.cnc_specs,
                cutting_specs=item.cutting_specs,
                preparation_specs=item.preparation_specs,
                packaging_notes=item.packaging_notes
            )
        
        # Создаем этапы заказа
        create_order_stages(order)
        
        # Обновляем статус заявки
        self.status = 'in_production'
        self.order = order
        self.save()
        
        return True, f"Заявка одобрена, создан заказ #{order.id}"


class RequestItem(models.Model):
    """Позиции заявки"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='items', verbose_name='Заявка')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='request_items', verbose_name='Товар')
    quantity = models.PositiveIntegerField('Количество', default=1)
    size = models.CharField('Размер', max_length=100, blank=True)
    color = models.CharField('Цвет', max_length=100, blank=True)
    price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2, default=0)
    
    # Дополнительные поля для передачи информации между цехами
    glass_type = models.CharField('Тип стекла', max_length=20, blank=True, help_text='Пескоструйный или УФ')
    paint_type = models.CharField('Тип краски', max_length=100, blank=True)
    paint_color = models.CharField('Цвет краски', max_length=100, blank=True)
    cnc_specs = models.TextField('Спецификации для ЧПУ', blank=True)
    cutting_specs = models.TextField('Спецификации для распила', blank=True)
    preparation_specs = models.TextField('Спецификации для цеха заготовки', blank=True, help_text='Комментарии и спецификации для цеха заготовки (ID 4)')
    packaging_notes = models.TextField('Заметки для упаковки', blank=True)
    
    class Meta:
        verbose_name = 'Позиция заявки'
        verbose_name_plural = 'Позиции заявки'
    
    def __str__(self):
        try:
            details = []
            if self.size:
                details.append(self.size)
            if self.color:
                details.append(self.color)
            if self.glass_type:
                details.append(f"стекло: {self.glass_type}")
            suffix = f" ({', '.join(details)})" if details else ''
            product_name = self.product.name if self.product else 'Не указан'
            return f"{product_name} x{self.quantity}{suffix}"
        except:
            return f"Товар x{self.quantity}"
    
    def save(self, *args, **kwargs):
        """Автоматически заполняем тип стекла при создании стеклянного изделия"""
        try:
            if self.product and self.product.is_glass and not self.glass_type:
                # По умолчанию устанавливаем пескоструйный тип
                self.glass_type = 'sandblasted'
        except:
            pass
        super().save(*args, **kwargs)
