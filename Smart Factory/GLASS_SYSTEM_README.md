# Система разделения стеклянных заказов

## Обзор

Система автоматически разделяет заказы по цехам в зависимости от типа товара:
- **Обычные товары** (`is_glass=False`) → Цех ID 1 (Распиловка)
- **Стеклянные товары** (`is_glass=True`) → Цех ID 2 (Распил стекла)

## Принцип работы

### 1. Создание заказа
При создании заказа система автоматически:
1. Анализирует все позиции заказа
2. Разделяет их на стеклянные и обычные
3. Создает отдельные этапы для каждого типа в соответствующих цехах

### 2. Параллельные потоки
- **Основной поток** (`parallel_group=None`): Обычные товары в цехе 1
- **Параллельный поток** (`parallel_group=1`): Стеклянные товары в цехе 2

### 3. Объединение в упаковке
После завершения обработки в цехах, товары объединяются в цехе упаковки (ID 12).

## Структура данных

### Модель Product
```python
class Product(models.Model):
    is_glass = models.BooleanField('Стеклянный', default=False)
    glass_type = models.CharField('Тип стекла', max_length=20, choices=GLASS_TYPES, null=True, blank=True)
```

### Модель Order
```python
class Order(models.Model):
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
```

### Модель OrderStage
```python
class OrderStage(models.Model):
    parallel_group = models.PositiveIntegerField('Группа параллельной обработки', null=True, blank=True)
    
    def is_glass_stage(self):
        """Проверяет, относится ли этап к обработке стекла"""
        return self.parallel_group == 1
```

## API Endpoints

### Получение заказов с разделением по цехам
```
GET /api/orders/by_workshop/
GET /api/orders/by_workshop/?workshop_id=1
GET /api/orders/by_workshop/?workshop_id=2
```

### Создание заказа
```
POST /api/orders/create/
```

## Команды управления

### Исправление существующих заказов
```bash
python manage.py fix_glass_orders
```

### Тестирование системы
```bash
python test_glass_system.py
```

## Примеры использования

### 1. Заказ только с обычными товарами
```python
order = Order.objects.create(name="Заказ обычных дверей", client=client)
OrderItem.objects.create(order=order, product=regular_product, quantity=2)
create_order_stages(order)
# Результат: 1 этап в цехе 1
```

### 2. Заказ только со стеклянными товарами
```python
order = Order.objects.create(name="Заказ стеклянных дверей", client=client)
OrderItem.objects.create(order=order, product=glass_product, quantity=1)
create_order_stages(order)
# Результат: 1 этап в цехе 2
```

### 3. Смешанный заказ
```python
order = Order.objects.create(name="Смешанный заказ", client=client)
OrderItem.objects.create(order=order, product=regular_product, quantity=1)
OrderItem.objects.create(order=order, product=glass_product, quantity=1)
create_order_stages(order)
# Результат: 2 этапа - в цехе 1 и цехе 2
```

## Workflow

### ORDER_WORKFLOW
```python
ORDER_WORKFLOW = [
    # Основной поток для обычных товаров (цех ID 1)
    {"workshop": 1, "operation": "Резка", "sequence": 1, "parallel_group": None},
    # Параллельный поток для стеклянных товаров (цех ID 2)
    {"workshop": 2, "operation": "Распил стекла", "sequence": 1, "parallel_group": 1},
]
```

## Мониторинг

### Статистика по цехам
- Цех 1: Количество заказов с обычными товарами
- Цех 2: Количество заказов со стеклянными товарами

### Отслеживание прогресса
- Каждый этап отслеживается отдельно
- Параллельные потоки могут завершаться независимо
- Объединение происходит на этапе упаковки

## Требования

### Цеха
- Цех ID 1: "Распиловка" (для обычных товаров)
- Цех ID 2: "Распил стекла" (для стеклянных товаров)
- Цех ID 12: "Упаковка готовой продукции" (объединение)

### Товары
- Поле `is_glass` должно быть корректно установлено
- Для стеклянных товаров рекомендуется указывать `glass_type`

## Обработка ошибок

### Отсутствующие цеха
Если цех не найден, система выводит предупреждение и пропускает создание этапа.

### Некорректные товары
Товары без указанного `product` игнорируются при создании этапов.

## Расширение системы

### Добавление новых типов товаров
1. Добавить новое поле в модель Product
2. Обновить логику в `create_order_stages()`
3. Добавить новый workflow в `ORDER_WORKFLOW`

### Добавление новых цехов
1. Создать цех в базе данных
2. Обновить `ORDER_WORKFLOW`
3. Обновить логику разделения в `create_order_stages()` 