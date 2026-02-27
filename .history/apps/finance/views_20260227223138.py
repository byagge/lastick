from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.core.paginator import Paginator

from .models import (
    ExpenseCategory, Supplier, SupplierItem, MainBankAccount, 
    MoneyMovement, Expense, Income, FactoryAsset, FinancialReport
)
from .forms import (
    ExpenseCategoryForm, SupplierForm, SupplierItemForm,
    MoneyMovementForm, ExpenseForm, IncomeForm, FactoryAssetForm, FinancialReportForm
)
from .forms import DebtForm, DebtPaymentForm
from .models import Debt, DebtPayment
from .models import AccountingAccount, JournalEntry, JournalEntryLine, AnalyticalAccount, StandardOperation, StandardOperationLine, AccountCorrespondence, FinancialPeriod, Request, RequestItem
from .forms import AccountingAccountForm, JournalEntryForm, JournalEntryLineForm, AnalyticalAccountForm, StandardOperationForm, StandardOperationLineForm, AccountCorrespondenceForm, FinancialPeriodForm, RequestForm, RequestItemForm

# Главная страница финансовой системы
@login_required
def finance_dashboard(request):
	"""Главный дашборд финансовой системы"""
	
	# Получаем основной счет
	main_account = MainBankAccount.get_main_account()
	total_balance = main_account.balance
	
	# Доходы и расходы за текущий месяц
	current_month = timezone.now().month
	current_year = timezone.now().year
	
	monthly_income = Income.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_expenses = Expense.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_profit = monthly_income - monthly_expenses
	
	# Общая стоимость активов
	total_assets = FactoryAsset.objects.filter(is_active=True).aggregate(
		total=Sum('current_value'))['total'] or Decimal('0.00')
	
	# Последние операции с оптимизацией
	recent_movements = MoneyMovement.objects.select_related('user').order_by('-date', '-id')[:5]
	recent_expenses = Expense.objects.select_related('category', 'supplier').order_by('-date', '-id')[:5]
	recent_incomes = Income.objects.select_related('created_by').order_by('-date', '-id')[:5]
	
	# Поставщики с предстоящими покупками (ограничиваем по дате)
	today = timezone.now().date()
	upcoming_purchases = SupplierItem.objects.select_related('supplier').filter(
		next_purchase_date__gte=today
	).order_by('next_purchase_date')[:5]
	
	context = {
		'total_balance': total_balance,
		'monthly_income': monthly_income,
		'monthly_expenses': monthly_expenses,
		'monthly_profit': monthly_profit,
		'total_assets': total_assets,
		'recent_movements': recent_movements,
		'recent_expenses': recent_expenses,
		'recent_incomes': recent_incomes,
		'upcoming_purchases': upcoming_purchases,
		'main_account': main_account,
	}
	
	return render(request, 'finance/dashboard.html', context)

# ==================== КАТЕГОРИИ РАСХОДОВ ====================
@login_required
def expense_categories(request):
	"""Список категорий расходов"""
	categories_qs = ExpenseCategory.objects.all().order_by('name', 'id')
	paginator = Paginator(categories_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'finance/expense_categories.html', {
		'categories': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
	})

@login_required
def expense_category_create(request):
	"""Создание новой категории расходов"""
	if request.method == 'POST':
		form = ExpenseCategoryForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Категория успешно создана!')
			return redirect('finance:expense_categories')
	else:
		form = ExpenseCategoryForm()
	
	return render(request, 'finance/expense_category_form.html', {'form': form, 'title': 'Новая категория'})

@login_required
def expense_category_edit(request, pk):
	"""Редактирование категории расходов"""
	category = get_object_or_404(ExpenseCategory, pk=pk)
	if request.method == 'POST':
		form = ExpenseCategoryForm(request.POST, instance=category)
		if form.is_valid():
			form.save()
			messages.success(request, 'Категория успешно обновлена!')
			return redirect('finance:expense_categories')
	else:
		form = ExpenseCategoryForm(instance=category)
	
	return render(request, 'finance/expense_category_form.html', {'form': form, 'title': 'Редактирование категории'})

@login_required
def expense_category_delete(request, pk):
	"""Удаление категории расходов"""
	category = get_object_or_404(ExpenseCategory, pk=pk)
	if request.method == 'POST':
		category.delete()
		messages.success(request, 'Категория успешно удалена!')
		return redirect('finance:expense_categories')
	
	return render(request, 'finance/expense_category_confirm_delete.html', {'category': category})

# ==================== ПОСТАВЩИКИ ====================
@login_required
def suppliers(request):
	"""Список поставщиков"""
	suppliers_qs = Supplier.objects.all().order_by('name', 'id')
	paginator = Paginator(suppliers_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'finance/suppliers.html', {
		'suppliers': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
	})

@login_required
def supplier_create(request):
	"""Создание нового поставщика"""
	if request.method == 'POST':
		form = SupplierForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Поставщик успешно создан!')
			return redirect('finance:suppliers')
	else:
		form = SupplierForm()
	
	return render(request, 'finance/supplier_form.html', {'form': form, 'title': 'Новый поставщик'})

@login_required
def supplier_edit(request, pk):
	"""Редактирование поставщика"""
	supplier = get_object_or_404(Supplier, pk=pk)
	if request.method == 'POST':
		form = SupplierForm(request.POST, instance=supplier)
		if form.is_valid():
			form.save()
			messages.success(request, 'Поставщик успешно обновлен!')
			return redirect('finance:suppliers')
	else:
		form = SupplierForm(instance=supplier)
	
	return render(request, 'finance/supplier_form.html', {'form': form, 'title': 'Редактирование поставщика'})

@login_required
def supplier_detail(request, pk):
	"""Детальная информация о поставщике"""
	supplier = get_object_or_404(Supplier, pk=pk)
	items_qs = SupplierItem.objects.filter(supplier=supplier).order_by('-next_purchase_date', '-id')
	# Статистика по расходам по поставщику
	expenses_qs = Expense.objects.filter(supplier=supplier)
	total_expenses = expenses_qs.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	expenses_count = expenses_qs.count()
	avg_expense = expenses_qs.aggregate(s=Sum('amount'))['s'] / expenses_count if expenses_count else Decimal('0.00')
	last_expense_date = expenses_qs.order_by('-date').values_list('date', flat=True).first()
	items_count = items_qs.count()
	recent_expenses = expenses_qs.order_by('-date', '-id')[:10]
	paginator = Paginator(items_qs, 20)
	page_obj = paginator.get_page(request.GET.get('page'))
	return render(request, 'finance/supplier_detail.html', {
		'supplier': supplier, 
		'items': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'total_expenses': total_expenses,
		'expenses_count': expenses_count,
		'avg_expense': avg_expense,
		'last_expense_date': last_expense_date,
		'items_count': items_count,
		'recent_expenses': recent_expenses,
	})

@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'Поставщик удален')
        return redirect('finance:suppliers')
    return render(request, 'finance/confirm_delete.html', {'object': supplier, 'title': 'Удалить поставщика'})

# ==================== ТОВАРЫ ПОСТАВЩИКОВ ====================
@login_required
def supplier_items(request):
	"""Список товаров поставщиков"""
	items_qs = SupplierItem.objects.select_related('supplier').all().order_by('-next_purchase_date', '-id')
	# Фильтры
	supplier_id = request.GET.get('supplier')
	search = request.GET.get('search')
	price_min = request.GET.get('price_min')
	price_max = request.GET.get('price_max')
	if supplier_id:
		items_qs = items_qs.filter(supplier_id=supplier_id)
	if search:
		items_qs = items_qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
	if price_min:
		try:
			items_qs = items_qs.filter(unit_price__gte=Decimal(price_min))
		except Exception:
			pass
	if price_max:
		try:
			items_qs = items_qs.filter(unit_price__lte=Decimal(price_max))
		except Exception:
			pass
	# Даты для индикации
	today = timezone.now().date()
	week_from_now = today + timedelta(days=7)
	# Статистика по отфильтрованным данным
	upcoming_items = items_qs.filter(next_purchase_date__gt=today, next_purchase_date__lte=week_from_now).count()
	overdue_items = items_qs.filter(next_purchase_date__lt=today).count()
	total_value = items_qs.aggregate(s=Sum('unit_price'))['s'] or Decimal('0.00')
	paginator = Paginator(items_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	suppliers = Supplier.objects.all().order_by('name')
	return render(request, 'finance/supplier_items.html', {
		'items': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'suppliers': suppliers,
		'today': today,
		'week_from_now': week_from_now,
		'upcoming_items': upcoming_items,
		'overdue_items': overdue_items,
		'total_value': total_value,
	})

@login_required
def supplier_item_create(request):
	"""Создание нового товара поставщика"""
	if request.method == 'POST':
		form = SupplierItemForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Товар поставщика успешно создан!')
			return redirect('finance:supplier_items')
	else:
		form = SupplierItemForm()
	
	return render(request, 'finance/supplier_item_form.html', {'form': form, 'title': 'Новый товар'})

# ==================== ДВИЖЕНИЕ ДЕНЕГ ====================
@login_required
def money_movements(request):
	"""Список движения денег"""
	movements_qs = MoneyMovement.objects.select_related('user').all().order_by('-date', '-id')
	movement_type = request.GET.get('movement_type')
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	if movement_type in {'deposit', 'withdrawal'}:
		movements_qs = movements_qs.filter(movement_type=movement_type)
	if date_from:
		try:
			parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
			movements_qs = movements_qs.filter(date__date__gte=parsed_from)
		except ValueError:
			pass
	if date_to:
		try:
			parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
			movements_qs = movements_qs.filter(date__date__lte=parsed_to)
		except ValueError:
			pass
	paginator = Paginator(movements_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	# Preserve filters in pagination
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	main_account = MainBankAccount.get_main_account()
	return render(request, 'finance/money_movements.html', {
		'movements': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'query_string': query_string,
		'main_account': main_account,
	})

@login_required
def money_movement_create(request):
	"""Создание нового движения денег"""
	if request.method == 'POST':
		form = MoneyMovementForm(request.POST)
		if form.is_valid():
			movement = form.save(commit=False)
			movement.user = request.user
			movement.save()
			messages.success(request, 'Движение денег успешно создано!')
			return redirect('finance:money_movements')
	else:
		form = MoneyMovementForm()
	
	return render(request, 'finance/money_movement_form.html', {'form': form, 'title': 'Новое движение'})

# ==================== РАСХОДЫ ====================
@login_required
def expenses(request):
	"""Управление расходами"""
	context = build_expenses_context(request)
	user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
	is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile'])
	template = 'finance/expenses_mobile.html' if is_mobile else 'finance/expenses.html'
	return render(request, template, context)


@login_required
def expenses_mobile(request):
	"""Mobile: расходы"""
	context = build_expenses_context(request)
	return render(request, 'finance/expenses_mobile.html', context)


def build_expenses_context(request):
	expenses_qs = Expense.objects.select_related('category', 'supplier', 'created_by').all().order_by('-date', '-id')
	category_id = request.GET.get('category')
	supplier_id = request.GET.get('supplier')
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	search = request.GET.get('search')
	amount_min = request.GET.get('amount_min')
	amount_max = request.GET.get('amount_max')
	if category_id:
		expenses_qs = expenses_qs.filter(category_id=category_id)
	if supplier_id:
		expenses_qs = expenses_qs.filter(supplier_id=supplier_id)
	if date_from:
		try:
			parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
			expenses_qs = expenses_qs.filter(date__gte=parsed_from)
		except ValueError:
			pass
	if date_to:
		try:
			parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
			expenses_qs = expenses_qs.filter(date__lte=parsed_to)
		except ValueError:
			pass
	if search:
		expenses_qs = expenses_qs.filter(
			Q(description__icontains=search) |
			Q(category__name__icontains=search) |
			Q(supplier__name__icontains=search) |
			Q(invoice_number__icontains=search)
		)
	if amount_min:
		try:
			expenses_qs = expenses_qs.filter(amount__gte=Decimal(amount_min))
		except Exception:
			pass
	if amount_max:
		try:
			expenses_qs = expenses_qs.filter(amount__lte=Decimal(amount_max))
		except Exception:
			pass
	total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	expenses_count = expenses_qs.count()
	avg_expense = (total_expenses / expenses_count) if expenses_count else Decimal('0.00')
	latest_expense_date = expenses_qs.values_list('date', flat=True).first()
	top_categories = list(
		expenses_qs.values('category__name')
		.annotate(total=Sum('amount'))
		.order_by('-total')[:5]
	)
	category_summary = []
	for row in top_categories:
		name = row.get('category__name') or 'Без категории'
		total = row.get('total') or Decimal('0.00')
		share = (total / total_expenses * 100) if total_expenses else Decimal('0.00')
		category_summary.append({'name': name, 'total': total, 'share': share})
	paginator = Paginator(expenses_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	categories = ExpenseCategory.objects.all()
	suppliers = Supplier.objects.all()
	return {
		'expenses': page_obj.object_list,
		'categories': categories,
		'suppliers': suppliers,
		'total_expenses': total_expenses,
		'expenses_count': expenses_count,
		'avg_expense': avg_expense,
		'latest_expense_date': latest_expense_date,
		'top_categories': category_summary,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'query_string': query_string,
	}


@login_required
def expense_create(request):
	"""Создание нового расхода"""
	if request.method == 'POST':
		form = ExpenseForm(request.POST)
		if form.is_valid():
			expense = form.save(commit=False)
			expense.created_by = request.user
			expense.save()
			messages.success(request, 'Расход успешно создан!')
			return redirect('finance:expenses')
	else:
		form = ExpenseForm()
	
	return render(request, 'finance/expense_form.html', {'form': form, 'title': 'Новый расход'})

@login_required
def expense_edit(request, pk):
	"""Редактирование расхода"""
	expense = get_object_or_404(Expense, pk=pk)
	if request.method == 'POST':
		form = ExpenseForm(request.POST, instance=expense)
		if form.is_valid():
			form.save()
			messages.success(request, 'Расход успешно обновлен!')
			return redirect('finance:expenses')
	else:
		form = ExpenseForm(instance=expense)
	
	return render(request, 'finance/expense_form.html', {'form': form, 'title': 'Редактирование расхода'})

# ==================== ДОХОДЫ ====================
@login_required
def incomes(request):
	"""Список доходов"""
	incomes_qs = Income.objects.select_related('created_by').all().order_by('-date', '-id')
	income_type = request.GET.get('income_type')
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	amount_min = request.GET.get('amount_min')
	amount_max = request.GET.get('amount_max')
	if income_type in {'sales', 'other'}:
		incomes_qs = incomes_qs.filter(income_type=income_type)
	if date_from:
		try:
			parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
			incomes_qs = incomes_qs.filter(date__gte=parsed_from)
		except ValueError:
			pass
	if date_to:
		try:
			parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
			incomes_qs = incomes_qs.filter(date__lte=parsed_to)
		except ValueError:
			pass
	if amount_min:
		try:
			incomes_qs = incomes_qs.filter(amount__gte=Decimal(amount_min))
		except Exception:
			pass
	if amount_max:
		try:
			incomes_qs = incomes_qs.filter(amount__lte=Decimal(amount_max))
		except Exception:
			pass
	total_income = incomes_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	income_count = incomes_qs.count()
	avg_income = (total_income / income_count) if income_count else Decimal('0.00')
	latest_income_date = incomes_qs.values_list('date', flat=True).first()
	paginator = Paginator(incomes_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	# Preserve filters in pagination
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	income_types = Income.INCOME_TYPES
	return render(request, 'finance/incomes.html', {
		'incomes': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'query_string': query_string,
		'income_types': income_types,
		'total_income': total_income,
		'income_count': income_count,
		'avg_income': avg_income,
		'latest_income_date': latest_income_date,
	})

@login_required
def income_create(request):
	"""Создание нового дохода"""
	if request.method == 'POST':
		form = IncomeForm(request.POST)
		if form.is_valid():
			income = form.save(commit=False)
			income.created_by = request.user
			income.save()
			messages.success(request, 'Доход успешно создан!')
			return redirect('finance:incomes')
	else:
		form = IncomeForm()
	
	return render(request, 'finance/income_form.html', {'form': form, 'title': 'Новый доход'})

# ==================== ИМУЩЕСТВО ЗАВОДА ====================
@login_required
def factory_assets(request):
	"""Список имущества завода"""
	assets_qs = FactoryAsset.objects.select_related('supplier').all().order_by('-current_value', '-id')
	search = request.GET.get('search')
	category = request.GET.get('category')
	status = request.GET.get('status')
	if search:
		assets_qs = assets_qs.filter(
			Q(name__icontains=search) |
			Q(description__icontains=search) |
			Q(location__icontains=search)
		)
	if category in {'building', 'equipment', 'vehicle', 'furniture', 'electronics', 'other'}:
		assets_qs = assets_qs.filter(asset_type=category)
	if status == 'active':
		assets_qs = assets_qs.filter(is_active=True)
	elif status == 'inactive':
		assets_qs = assets_qs.filter(is_active=False)
	total_current_value = assets_qs.aggregate(total=Sum('current_value'))['total'] or Decimal('0.00')
	total_purchase_value = assets_qs.aggregate(total=Sum('purchase_price'))['total'] or Decimal('0.00')
	assets_count = assets_qs.count()
	active_assets = assets_qs.filter(is_active=True).count()
	avg_asset_value = (total_current_value / assets_count) if assets_count else Decimal('0.00')
	paginator = Paginator(assets_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	return render(request, 'finance/factory_assets.html', {
		'assets': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'query_string': query_string,
		'total_current_value': total_current_value,
		'total_purchase_value': total_purchase_value,
		'assets_count': assets_count,
		'active_assets': active_assets,
		'avg_asset_value': avg_asset_value,
	})

@login_required
def factory_asset_create(request):
	"""Создание нового имущества"""
	if request.method == 'POST':
		form = FactoryAssetForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Имущество успешно добавлено!')
			return redirect('finance:factory_assets')
	else:
		form = FactoryAssetForm()
	
	return render(request, 'finance/factory_asset_form.html', {'form': form, 'title': 'Новое имущество'})

@login_required
def factory_asset_detail(request, pk):
	asset = get_object_or_404(FactoryAsset, pk=pk)
	return render(request, 'finance/factory_asset_detail.html', {'asset': asset})

@login_required
def factory_asset_edit(request, pk):
	asset = get_object_or_404(FactoryAsset, pk=pk)
	if request.method == 'POST':
		form = FactoryAssetForm(request.POST, instance=asset)
		if form.is_valid():
			form.save()
			messages.success(request, 'Имущество обновлено')
			return redirect('finance:factory_assets')
	else:
		form = FactoryAssetForm(instance=asset)
	return render(request, 'finance/factory_asset_form.html', {'form': form})

@login_required
def factory_asset_delete(request, pk):
	asset = get_object_or_404(FactoryAsset, pk=pk)
	if request.method == 'POST':
		asset.delete()
		messages.success(request, 'Имущество удалено')
		return redirect('finance:factory_assets')
	return render(request, 'finance/confirm_delete.html', {'object': asset, 'title': 'Удалить имущество'})

# ==================== ФИНАНСОВЫЕ ОТЧЕТЫ ====================
@login_required
def financial_reports(request):
	"""Список финансовых отчетов"""
	reports_qs = FinancialReport.objects.select_related('created_by').all().order_by('-start_date', '-id')
	search = request.GET.get('search')
	period = request.GET.get('period')
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	if search:
		reports_qs = reports_qs.filter(title__icontains=search)
	if period in {'monthly', 'quarterly', 'yearly', 'custom'}:
		reports_qs = reports_qs.filter(report_type=period)
	if date_from:
		try:
			parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
			reports_qs = reports_qs.filter(start_date__gte=parsed_from)
		except ValueError:
			pass
	if date_to:
		try:
			parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
			reports_qs = reports_qs.filter(end_date__lte=parsed_to)
		except ValueError:
			pass
	reports_count = reports_qs.count()
	latest_report = reports_qs.first()
	paginator = Paginator(reports_qs, 25)
	page_obj = paginator.get_page(request.GET.get('page'))
	query_params = request.GET.copy()
	query_params.pop('page', None)
	query_string = query_params.urlencode()
	
	# Сводные показатели
	total_income = Income.objects.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	total_expenses = Expense.objects.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	net_profit = total_income - total_expenses
	
	context = {
		'reports': page_obj.object_list,
		'page_obj': page_obj,
		'is_paginated': page_obj.paginator.num_pages > 1,
		'total_income': total_income,
		'total_expenses': total_expenses,
		'total_profit': net_profit,
		'reports_count': reports_count,
		'latest_report': latest_report,
		'query_string': query_string,
	}
	return render(request, 'finance/financial_reports.html', context)

@login_required
def financial_report_create(request):
	"""Создание нового финансового отчета"""
	if request.method == 'POST':
		form = FinancialReportForm(request.POST)
		if form.is_valid():
			report = form.save(commit=False)
			report.created_by = request.user
			
			# Получаем дополнительные поля из формы
			report.title = request.POST.get('title', '')
			report.start_date = request.POST.get('start_date')
			report.end_date = request.POST.get('end_date')
			
			report.save()
			report.calculate_totals()  # Рассчитываем показатели
			messages.success(request, 'Финансовый отчет успешно создан!')
			return redirect('finance:financial_reports')
	else:
		form = FinancialReportForm()
	
	return render(request, 'finance/financial_report_form.html', {'form': form, 'title': 'Новый отчет'})

@login_required
def financial_report_export_excel(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	report.calculate_totals()
	from django.http import HttpResponse
	# Генерируем HTML-таблицу, совместимую с Excel
	html = []
	html.append('<html><head><meta charset="utf-8"></head><body>')
	html.append(f'<h2>{report.title}</h2>')
	html.append(f'<p>Период: {report.start_date} - {report.end_date}</p>')
	html.append('<table border="1" cellspacing="0" cellpadding="4">')
	html.append('<tr><th>Показатель</th><th>Значение</th></tr>')
	html.append(f'<tr><td>Общий доход</td><td>{report.total_income}</td></tr>')
	html.append(f'<tr><td>Общий расход</td><td>{report.total_expenses}</td></tr>')
	html.append(f'<tr><td>Чистая прибыль</td><td>{report.net_income}</td></tr>')
	html.append(f'<tr><td>Операционный доход</td><td>{report.operating_income}</td></tr>')
	html.append(f'<tr><td>Общие активы</td><td>{report.total_assets}</td></tr>')
	html.append('</table>')
	# Детализация доходов/расходов
	incomes = Income.objects.filter(date__range=[report.start_date, report.end_date]).order_by('-amount')[:500]
	expenses = Expense.objects.filter(date__range=[report.start_date, report.end_date]).order_by('-amount')[:500]
	html.append('<h3>Доходы</h3>')
	html.append('<table border="1" cellspacing="0" cellpadding="4">')
	html.append('<tr><th>Дата</th><th>Тип</th><th>Сумма</th><th>Описание</th></tr>')
	for inc in incomes:
		html.append(f'<tr><td>{inc.date}</td><td>{inc.get_income_type_display()}</td><td>{inc.amount}</td><td>{inc.description}</td></tr>')
	html.append('</table>')
	html.append('<h3>Расходы</h3>')
	html.append('<table border="1" cellspacing="0" cellpadding="4">')
	html.append('<tr><th>Дата</th><th>Категория</th><th>Поставщик</th><th>Сумма</th><th>Описание</th></tr>')
	for exp in expenses:
		cat = exp.category.name if exp.category_id else ''
		supp = exp.supplier.name if exp.supplier_id else ''
		html.append(f'<tr><td>{exp.date}</td><td>{cat}</td><td>{supp}</td><td>{exp.amount}</td><td>{exp.description}</td></tr>')
	html.append('</table>')
	html.append('</body></html>')
	content = ''.join(html)
	response = HttpResponse(content, content_type='application/vnd.ms-excel; charset=utf-8')
	response['Content-Disposition'] = f'attachment; filename="financial_report_{report.pk}.xls"'
	return response

# Уточним детальный отчет: добавим разбивки и топы
@login_required
def financial_report_detail(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	profit_margin_pct = None
	if report.total_income and report.total_income != 0:
		try:
			profit_margin_pct = (report.net_income / report.total_income) * 100
		except Exception:
			profit_margin_pct = None
	# Подробная аналитика
	incomes_qs = Income.objects.filter(date__range=[report.start_date, report.end_date])
	expenses_qs = Expense.objects.filter(date__range=[report.start_date, report.end_date])
	from django.db.models import Count
	income_by_type = list(incomes_qs.values('income_type').annotate(total=Sum('amount'), cnt=Count('id')).order_by('-total'))
	expense_by_category = list(expenses_qs.values('category__name').annotate(total=Sum('amount'), cnt=Count('id')).order_by('-total'))
	top_incomes = incomes_qs.order_by('-amount')[:10]
	top_expenses = expenses_qs.order_by('-amount')[:10]
	# Динамика по дням
	daily_income = list(incomes_qs.values('date').annotate(total=Sum('amount')).order_by('date'))
	daily_expenses = list(expenses_qs.values('date').annotate(total=Sum('amount')).order_by('date'))
	context = {
		'report': report,
		'profit_margin_pct': profit_margin_pct,
		'income_by_type': income_by_type,
		'expense_by_category': expense_by_category,
		'top_incomes': top_incomes,
		'top_expenses': top_expenses,
		'daily_income': daily_income,
		'daily_expenses': daily_expenses,
	}
	return render(request, 'finance/financial_report_detail.html', context)

@login_required
def financial_report_edit(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	if request.method == 'POST':
		form = FinancialReportForm(request.POST, instance=report)
		if form.is_valid():
			report = form.save(commit=False)
			report.title = request.POST.get('title', report.title)
			report.start_date = request.POST.get('start_date') or report.start_date
			report.end_date = request.POST.get('end_date') or report.end_date
			report.save()
			report.calculate_totals()
			messages.success(request, 'Отчет обновлен')
			return redirect('finance:financial_reports')
	else:
		form = FinancialReportForm(instance=report)
	return render(request, 'finance/financial_report_form.html', {'form': form, 'report': report})

@login_required
def financial_report_delete(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	if request.method == 'POST':
		report.delete()
		messages.success(request, 'Отчет удален')
		return redirect('finance:financial_reports')
	return render(request, 'finance/confirm_delete.html', {'object': report, 'title': 'Удалить отчет'})

@login_required
def financial_report_export_csv(request, pk):
	report = get_object_or_404(FinancialReport, pk=pk)
	# Ensure totals are up to date
	report.calculate_totals()
	import csv
	from django.http import HttpResponse
	response = HttpResponse(content_type='text/csv; charset=utf-8')
	response['Content-Disposition'] = f'attachment; filename="financial_report_{report.pk}.csv"'
	writer = csv.writer(response)
	writer.writerow(['Название', report.title])
	writer.writerow(['Период', f"{report.start_date} - {report.end_date}"])
	writer.writerow([])
	writer.writerow(['Показатель', 'Значение'])
	writer.writerow(['Общий доход', report.total_income])
	writer.writerow(['Общий расход', report.total_expenses])
	writer.writerow(['Чистая прибыль', report.net_income])
	writer.writerow(['Операционный доход', report.operating_income])
	writer.writerow(['Общие активы', report.total_assets])
	return response

# ==================== API ДЛЯ AJAX ====================
@login_required
def get_expense_categories(request):
	"""API для получения категорий расходов"""
	categories = ExpenseCategory.objects.all().order_by('name')[:100]  # Ограничиваем количество
	data = [{'id': cat.id, 'name': cat.name} for cat in categories]
	return JsonResponse(data, safe=False)

@login_required
def get_suppliers(request):
	"""API для получения поставщиков"""
	suppliers = Supplier.objects.all().order_by('name')[:100]  # Ограничиваем количество
	data = [{'id': sup.id, 'name': sup.name} for sup in suppliers]
	return JsonResponse(data, safe=False)

# ==================== ДЕТАЛЬНЫЕ ПРОСМОТРЫ ====================
@login_required
def expense_details(request, pk):
	"""Детальная информация о расходе"""
	expense = get_object_or_404(Expense, pk=pk)
	return render(request, 'finance/expense_details.html', {'expense': expense})

@login_required
def income_details(request, pk):
	"""Детальная информация о доходе"""
	income = get_object_or_404(Income, pk=pk)
	return render(request, 'finance/income_details.html', {'income': income})

@login_required
def money_movement_details(request, pk):
	"""Детальная информация об операции"""
	movement = get_object_or_404(MoneyMovement, pk=pk)
	return render(request, 'finance/money_movement_details.html', {'movement': movement})

@login_required
def supplier_item_details(request, pk):
	"""Детальная информация о товаре поставщика"""
	item = get_object_or_404(SupplierItem, pk=pk)
	today = timezone.now().date()
	week_from_now = today + timedelta(days=7)
	return render(request, 'finance/supplier_item_details.html', {
		'item': item,
		'today': today,
		'week_from_now': week_from_now,
	})

@login_required
def supplier_item_edit(request, pk):
	item = get_object_or_404(SupplierItem, pk=pk)
	if request.method == 'POST':
		form = SupplierItemForm(request.POST, instance=item)
		if form.is_valid():
			form.save()
			messages.success(request, 'Товар обновлен')
			return redirect('finance:supplier_items')
	else:
		form = SupplierItemForm(instance=item)
	return render(request, 'finance/supplier_item_form.html', {'form': form, 'title': 'Редактирование товара'})

@login_required
def supplier_item_delete(request, pk):
	item = get_object_or_404(SupplierItem, pk=pk)
	if request.method == 'POST':
		item.delete()
		messages.success(request, 'Товар удален')
		return redirect('finance:supplier_items')
	return render(request, 'finance/confirm_delete.html', {'object': item, 'title': 'Удалить товар'})

@login_required
def dashboard_stats(request):
	"""API для получения статистики дашборда"""
	# Получаем основной счет
	main_account = MainBankAccount.get_main_account()
	total_balance = main_account.balance
	
	# Доходы и расходы за текущий месяц
	current_month = timezone.now().month
	current_year = timezone.now().year
	
	monthly_income = Income.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_expenses = Expense.objects.filter(
		date__month=current_month,
		date__year=current_year
	).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	monthly_profit = monthly_income - monthly_expenses
	
	# Общая стоимость активов
	total_assets = FactoryAsset.objects.filter(is_active=True).aggregate(
		total=Sum('current_value'))['total'] or Decimal('0.00')
	
	data = {
		'total_balance': float(total_balance),
		'monthly_income': float(monthly_income),
		'monthly_expenses': float(monthly_expenses),
		'monthly_profit': float(monthly_profit),
		'total_assets': float(total_assets),
	}
	
	return JsonResponse(data)

# ==================== ДОЛГИ ====================
@login_required
def debts(request):
    """Список долгов"""
    debts_qs = Debt.objects.select_related('supplier', 'created_by').all().order_by('-created_at', '-id')
    direction = request.GET.get('direction')
    status = request.GET.get('status')
    if direction in {'payable', 'receivable'}:
        debts_qs = debts_qs.filter(direction=direction)
    if status in {'open', 'partial', 'closed'}:
        if status == 'open':
            debts_qs = debts_qs.filter(amount_paid=Decimal('0.00'))
        elif status == 'partial':
            debts_qs = debts_qs.filter(amount_paid__gt=Decimal('0.00')).exclude(amount_paid__gte=F('original_amount'))
        else:
            debts_qs = debts_qs.filter(amount_paid__gte=F('original_amount'))
    total_original = debts_qs.aggregate(total=Sum('original_amount'))['total'] or Decimal('0.00')
    total_paid = debts_qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    total_outstanding = total_original - total_paid
    today = timezone.now().date()
    overdue_count = debts_qs.filter(due_date__lt=today).exclude(amount_paid__gte=F('original_amount')).count()
    paginator = Paginator(debts_qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()
    return render(request, 'finance/debts.html', {
        'debts': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.paginator.num_pages > 1,
        'query_string': query_string,
        'total_original': total_original,
        'total_paid': total_paid,
        'total_outstanding': total_outstanding,
        'overdue_count': overdue_count,
    })

@login_required
def debt_create(request):
    """Создание нового долга"""
    if request.method == 'POST':
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save(commit=False)
            debt.created_by = request.user
            debt.save()
            messages.success(request, 'Долг успешно создан!')
            return redirect('finance:debts')
    else:
        form = DebtForm()
    return render(request, 'finance/debt_form.html', {'form': form, 'title': 'Новый долг'})

@login_required
def debt_detail(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    payments = debt.payments.select_related('created_by').all().order_by('-date', '-id')
    payment_form = DebtPaymentForm()
    return render(request, 'finance/debt_detail.html', {'debt': debt, 'payments': payments, 'payment_form': payment_form})

@login_required
def debt_add_payment(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    if request.method == 'POST':
        form = DebtPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.debt = debt
            payment.created_by = request.user
            # Валидация: нельзя оплатить больше остатка
            if payment.amount > debt.outstanding_amount:
                messages.error(request, 'Сумма оплаты превышает остаток долга')
            else:
                payment.save()
                messages.success(request, 'Оплата добавлена!')
                return redirect('finance:debt_detail', pk=debt.pk)
    return redirect('finance:debt_detail', pk=debt.pk)

@login_required
def debt_delete(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    if request.method == 'POST':
        debt.delete()
        messages.success(request, 'Долг удален')
        return redirect('finance:debts')
    return render(request, 'finance/confirm_delete.html', {'object': debt, 'title': 'Удалить долг'})

@login_required
def accounts(request):
	qs = AccountingAccount.objects.select_related('parent').order_by('code')
	
	# Подсчитываем статистику
	total_accounts = qs.count()
	active_accounts = qs.filter(is_active=True).count()
	group_accounts = qs.filter(parent__isnull=True).count()
	sub_accounts = qs.filter(parent__isnull=False).count()
	
	return render(request, 'finance/accounts.html', {
		'accounts': qs,
		'total_accounts': total_accounts,
		'active_accounts': active_accounts,
		'group_accounts': group_accounts,
		'sub_accounts': sub_accounts,
	})

@login_required
def account_create(request):
	if request.method == 'POST':
		form = AccountingAccountForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Счет создан')
			return redirect('finance:accounts')
	else:
		form = AccountingAccountForm()
	return render(request, 'finance/account_form.html', {'form': form, 'title': 'Новый счет'})

@login_required
def account_edit(request, pk):
	acc = get_object_or_404(AccountingAccount, pk=pk)
	if request.method == 'POST':
		form = AccountingAccountForm(request.POST, instance=acc)
		if form.is_valid():
			form.save()
			messages.success(request, 'Счет обновлен')
			return redirect('finance:accounts')
	else:
		form = AccountingAccountForm(instance=acc)
	return render(request, 'finance/account_form.html', {'form': form, 'title': 'Редактирование счета'})

@login_required
def journal_entries(request):
	entries = JournalEntry.objects.prefetch_related('lines__account').order_by('-date', '-created_at')
	
	# Получаем текущую дату для статистики
	from django.utils import timezone
	today = timezone.now().date()
	current_month = timezone.now().month
	
	# Подсчитываем статистику
	total_entries = entries.count()
	posted_entries = entries.filter(posted=True).count()
	today_entries = entries.filter(date=today).count()
	month_entries = entries.filter(date__month=current_month).count()
	
	return render(request, 'finance/journal_entries.html', {
		'entries': entries,
		'total_entries': total_entries,
		'posted_entries': posted_entries,
		'today_entries': today_entries,
		'month_entries': month_entries,
		'today': today,
		'current_month': current_month,
	})

@login_required
def journal_entry_create(request):
	if request.method == 'POST':
		form = JournalEntryForm(request.POST)
		line_form = JournalEntryLineForm(request.POST, prefix='line')
		if form.is_valid() and line_form.is_valid():
			from decimal import Decimal as _D
			# Pre-validate totals from POST without saving anything
			first_debit = line_form.cleaned_data.get('debit') or _D('0')
			first_credit = line_form.cleaned_data.get('credit') or _D('0')
			total_debit = first_debit
			total_credit = first_credit
			indices = set()
			for key in request.POST.keys():
				if key.startswith('line_') and key.endswith('_account'):
					try:
						idx = int(key.split('_')[1])
						indices.add(idx)
					except Exception:
						pass
			for idx in sorted(indices):
				debit_val = request.POST.get(f'line_{idx}_debit')
				credit_val = request.POST.get(f'line_{idx}_credit')
				account_val = request.POST.get(f'line_{idx}_account')
				try:
					debit_amt = _D(debit_val or '0')
					credit_amt = _D(credit_val or '0')
				except Exception:
					debit_amt = _D('0')
					credit_amt = _D('0')
				total_debit += debit_amt
				total_credit += credit_amt
			if total_debit.quantize(_D('0.01')) != total_credit.quantize(_D('0.01')):
				messages.error(request, f"Баланс не сходится: Дт={total_debit} Кт={total_credit}")
				return render(request, 'finance/journal_entry_form.html', {
					'form': form,
					'line_form': line_form,
					'title': 'Новая операция',
					'accounts': AccountingAccount.objects.filter(is_active=True).order_by('code'),
					'lineCounter': 1
				})
			# Save after validation
			from django.db import transaction
			with transaction.atomic():
				entry = form.save(commit=False)
				entry.created_by = request.user
				entry.save()
				first_line = line_form.save(commit=False)
				first_line.entry = entry
				first_line.save()
				for idx in sorted(indices):
					account_id = request.POST.get(f'line_{idx}_account')
					debit_val = request.POST.get(f'line_{idx}_debit')
					credit_val = request.POST.get(f'line_{idx}_credit')
					desc_val = request.POST.get(f'line_{idx}_description', '')
					if not account_id:
						continue
					JournalEntryLine.objects.create(
						entry=entry,
						account_id=account_id,
						description=desc_val,
						debit=_D(debit_val or '0'),
						credit=_D(credit_val or '0'),
					)
			messages.success(request, 'Операция создана')
			return redirect('finance:journal_entries')
	else:
		form = JournalEntryForm()
		line_form = JournalEntryLineForm(prefix='line')
	
	# Получаем список активных счетов для формы
	accounts = AccountingAccount.objects.filter(is_active=True).order_by('code')
	
	return render(request, 'finance/journal_entry_form.html', {
		'form': form, 
		'line_form': line_form, 
		'title': 'Новая операция',
		'accounts': accounts,
		'lineCounter': 1
	})

@login_required
def journal_entry_detail(request, pk):
	entry = get_object_or_404(JournalEntry.objects.prefetch_related('lines__account'), pk=pk)
	line_form = JournalEntryLineForm()
	if request.method == 'POST':
		form = JournalEntryLineForm(request.POST)
		if form.is_valid():
			line = form.save(commit=False)
			line.entry = entry
			line.save()
			messages.success(request, 'Строка добавлена')
			return redirect('finance:journal_entry_detail', pk=entry.pk)
	return render(request, 'finance/journal_entry_detail.html', {'entry': entry, 'line_form': line_form})

@login_required
def journal_entry_add_line(request, pk):
	entry = get_object_or_404(JournalEntry, pk=pk)
	if request.method == 'POST':
		form = JournalEntryLineForm(request.POST)
		if form.is_valid():
			line = form.save(commit=False)
			line.entry = entry
			line.save()
			messages.success(request, 'Строка добавлена')
			return redirect('finance:journal_entries')
	return redirect('finance:journal_entries')

@login_required
def journal_entry_export(request, format):
	"""Экспорт журнальной операции в различных форматах"""
	from django.http import JsonResponse, HttpResponse
	import json
	from datetime import datetime
	
	# Получаем данные из запроса
	date = request.GET.get('date', '')
	memo = request.GET.get('memo', '')
	posted = request.GET.get('posted', 'false') == 'true'
	
	# Собираем строки проводки
	lines = []
	line_index = 1
	while True:
		account = request.GET.get(f'line_{line_index}_account', '')
		debit = request.GET.get(f'line_{line_index}_debit', '0')
		credit = request.GET.get(f'line_{line_index}_credit', '0')
		description = request.GET.get(f'line_{line_index}_description', '')
		
		if not account and not debit and not credit:
			break
			
		lines.append({
			'account': account,
			'debit': float(debit) if debit else 0,
			'credit': float(credit) if credit else 0,
			'description': description
		})
		line_index += 1
	
	# Формируем данные операции
	operation_data = {
		'date': date,
		'memo': memo,
		'posted': posted,
		'lines': lines,
		'exported_at': datetime.now().isoformat(),
		'export_format': format
	}
	
	if format == 'json':
		return JsonResponse(operation_data, json_dumps_params={'indent': 2})
	elif format == 'xml':
		"""?????????? ?????????"""
		"""<journal_entry>
			<date>{date}</date>
			<memo>{memo}</memo>
			<posted>{posted}</posted>
			<lines>"""
				
		for line in lines:
			xml_content += f"""
<line>
					<account>{line['account']}</account>
					<debit>{line['debit']}</debit>
					<credit>{line['credit']}</credit>
					<description>{line['description']}</description>
				</line>"""
				
				xml_content += """
			</lines>
			<exported_at>{}</exported_at>
			<export_format>{}</export_format>
		</journal_entry>""".format(datetime.now().isoformat(), format)
		
		response = HttpResponse(xml_content, content_type='application/xml')
		response['Content-Disposition'] = f'attachment; filename="journal_entry_{date}.xml"'
		return response
	else:
		return JsonResponse({'error': 'Неподдерживаемый формат экспорта'}, status=400)

@login_required
def trial_balance(request):
	# Оборотно-сальдовая ведомость
	date_from = request.GET.get('date_from')
	date_to = request.GET.get('date_to')
	from datetime import datetime as _dt
	from django.utils import timezone
	
	# Если даты не указаны, устанавливаем текущий месяц по умолчанию
	if not date_from or not date_to:
		now = timezone.now()
		date_from = now.replace(day=1).strftime('%Y-%m-%d')
		date_to = now.strftime('%Y-%m-%d')
	
	df = _dt.strptime(date_from, '%Y-%m-%d').date() if date_from else None
	dt = _dt.strptime(date_to, '%Y-%m-%d').date() if date_to else None
	
	rows = []
	total_debit = Decimal('0.00')
	total_credit = Decimal('0.00')
	
	for acc in AccountingAccount.objects.order_by('code'):
		b = acc.get_balance(df, dt)
		rows.append({'account': acc, **b})
		total_debit += b['debit_turnover']
		total_credit += b['credit_turnover']
	
	# Получаем текущую дату для статистики
	today = timezone.now().date()
	current_month = timezone.now().month
	
	return render(request, 'finance/trial_balance.html', {
		'rows': rows,
		'total_debit': total_debit,
		'total_credit': total_credit,
		'date_from': date_from,
		'date_to': date_to,
		'today': today,
		'current_month': current_month,
	})

# ====== РАСШИРЕННАЯ БУХГАЛТЕРИЯ ======

@login_required
def analytical_accounts(request):
	"""Список аналитических счетов"""
	accounts = AnalyticalAccount.objects.select_related('parent_account').order_by('parent_account__code', 'code')
	return render(request, 'finance/analytical_accounts.html', {'accounts': accounts})

@login_required
def analytical_account_create(request):
	"""Создание аналитического счета"""
	if request.method == 'POST':
		form = AnalyticalAccountForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Аналитический счет создан')
			return redirect('finance:analytical_accounts')
	else:
		form = AnalyticalAccountForm()
	return render(request, 'finance/analytical_account_form.html', {'form': form, 'title': 'Новый аналитический счет'})

@login_required
def analytical_account_edit(request, pk):
	"""Редактирование аналитического счета"""
	account = get_object_or_404(AnalyticalAccount, pk=pk)
	if request.method == 'POST':
		form = AnalyticalAccountForm(request.POST, instance=account)
		if form.is_valid():
			form.save()
			messages.success(request, 'Аналитический счет обновлен')
			return redirect('finance:analytical_accounts')
	else:
		form = AnalyticalAccountForm(instance=account)
	return render(request, 'finance/analytical_account_form.html', {'form': form, 'title': 'Редактирование аналитического счета'})

@login_required
def standard_operations(request):
	"""Список типовых операций"""
	operations = StandardOperation.objects.select_related('created_by').order_by('category', 'name')
	return render(request, 'finance/standard_operations.html', {'operations': operations})

@login_required
def standard_operation_create(request):
	"""Создание типовой операции"""
	if request.method == 'POST':
		form = StandardOperationForm(request.POST)
		if form.is_valid():
			operation = form.save(commit=False)
			operation.created_by = request.user
			operation.save()
			messages.success(request, 'Типовая операция создана')
			return redirect('finance:standard_operations')
	else:
		form = StandardOperationForm()
	return render(request, 'finance/standard_operation_form.html', {'form': form, 'title': 'Новая типовая операция'})

@login_required
def standard_operation_detail(request, pk):
	"""Детали типовой операции"""
	operation = get_object_or_404(StandardOperation, pk=pk)
	return render(request, 'finance/standard_operation_detail.html', {'operation': operation})

@login_required
def standard_operation_edit(request, pk):
	"""Редактирование типовой операции"""
	operation = get_object_or_404(StandardOperation, pk=pk)
	if request.method == 'POST':
		form = StandardOperationForm(request.POST, instance=operation)
		if form.is_valid():
			form.save()
			messages.success(request, 'Типовая операция обновлена')
			return redirect('finance:standard_operations')
	else:
		form = StandardOperationForm(instance=operation)
	return render(request, 'finance/standard_operation_form.html', {'form': form, 'title': 'Редактирование типовой операции'})

@login_required
def account_correspondences(request):
	"""Список корреспонденций счетов"""
	correspondences = AccountCorrespondence.objects.select_related('debit_account', 'credit_account').order_by('debit_account__code', 'credit_account__code')
	return render(request, 'finance/account_correspondences.html', {'correspondences': correspondences})

@login_required
def account_correspondence_create(request):
	"""Создание корреспонденции счетов"""
	if request.method == 'POST':
		form = AccountCorrespondenceForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Корреспонденция создана')
			return redirect('finance:account_correspondences')
	else:
		form = AccountCorrespondenceForm()
	return render(request, 'finance/account_correspondence_form.html', {'form': form, 'title': 'Новая корреспонденция'})

@login_required
def account_correspondence_edit(request, pk):
	"""Редактирование корреспонденции счетов"""
	correspondence = get_object_or_404(AccountCorrespondence, pk=pk)
	if request.method == 'POST':
		form = AccountCorrespondenceForm(request.POST, instance=correspondence)
		if form.is_valid():
			form.save()
			messages.success(request, 'Корреспонденция обновлена')
			return redirect('finance:account_correspondences')
	else:
		form = AccountCorrespondenceForm(instance=correspondence)
	return render(request, 'finance/account_correspondence_form.html', {'form': form, 'title': 'Редактирование корреспонденции'})

@login_required
def financial_periods(request):
	"""Список финансовых периодов"""
	periods = FinancialPeriod.objects.select_related('closed_by').order_by('-start_date')
	return render(request, 'finance/financial_periods.html', {'periods': periods})

@login_required
def financial_period_create(request):
	"""Создание финансового периода"""
	if request.method == 'POST':
		form = FinancialPeriodForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Финансовый период создан')
			return redirect('finance:financial_periods')
	else:
		form = FinancialPeriodForm()
	return render(request, 'finance/financial_period_form.html', {'form': form, 'title': 'Новый финансовый период'})

@login_required
def financial_period_close(request, pk):
	"""Закрытие финансового периода"""
	period = get_object_or_404(FinancialPeriod, pk=pk)
	if request.method == 'POST':
		period.close_period(request.user)
		messages.success(request, f'Период "{period.name}" закрыт')
		return redirect('finance:financial_periods')
	return render(request, 'finance/financial_period_close_confirm.html', {'period': period})

@login_required
def financial_period_edit(request, pk):
	"""Редактирование финансового периода"""
	period = get_object_or_404(FinancialPeriod, pk=pk)
	if request.method == 'POST':
		form = FinancialPeriodForm(request.POST, instance=period)
		if form.is_valid():
			form.save()
			messages.success(request, 'Финансовый период обновлен')
			return redirect('finance:financial_periods')
	else:
		form = FinancialPeriodForm(instance=period)
	return render(request, 'finance/financial_period_form.html', {'form': form, 'title': 'Редактирование финансового периода'})


# ===== ЗАЯВКИ =====

@login_required
def requests_list(request):
	"""Список заявок"""
	# Определяем мобильное устройство
	user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
	is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile'])
	
	requests = Request.objects.select_related('client').prefetch_related('items__product').order_by('-created_at')
	
	# Выбираем шаблон в зависимости от устройства (шаблоны перенесены в apps/orders)
	template = 'orders/requests_mobile.html' if is_mobile else 'orders/requests.html'
	return render(request, template, {'requests': requests})


@login_required
def request_create(request):
	"""Создание заявки"""
	if request.method == 'POST':
		form = RequestForm(request.POST)
		if form.is_valid():
			request_obj = form.save()
			messages.success(request, 'Заявка создана')
			return redirect('finance:request_detail', pk=request_obj.pk)
	else:
		form = RequestForm()
	return render(request, 'finance/request_form.html', {'form': form, 'title': 'Новая заявка'})


@login_required
def request_detail(request, pk):
	"""Детали заявки"""
	request_obj = get_object_or_404(Request, pk=pk)
	return render(request, 'finance/request_detail.html', {'request': request_obj})


@login_required
def request_edit(request, pk):
	"""Редактирование заявки"""
	request_obj = get_object_or_404(Request, pk=pk)
	if request.method == 'POST':
		form = RequestForm(request.POST, instance=request_obj)
		if form.is_valid():
			form.save()
			messages.success(request, 'Заявка обновлена')
			return redirect('finance:request_detail', pk=request_obj.pk)
	else:
		form = RequestForm(instance=request_obj)
	return render(request, 'finance/request_form.html', {'form': form, 'title': 'Редактирование заявки'})


@login_required
def request_delete(request, pk):
	"""Удаление заявки"""
	request_obj = get_object_or_404(Request, pk=pk)
	if request.method == 'POST':
		request_obj.delete()
		messages.success(request, 'Заявка удалена')
		return redirect('finance:requests')
	return render(request, 'finance/request_delete_confirm.html', {'request': request_obj})


# API для заявок
@login_required
def get_requests(request):
	"""API: получение списка заявок"""
	requests = Request.objects.select_related('client').prefetch_related('items__product').order_by('-created_at')
	data = []
	for req in requests:
		data.append({
			'id': req.id,
			'name': req.name,
			'client': {
				'id': req.client.id,
				'name': req.client.name,
				'company': req.client.company,
				'phone': req.client.phone,
				'email': req.client.email,
				'address': req.client.address,
			} if req.client else None,
			'status': req.status,
			'status_display': req.status_display,
			'created_at': req.created_at.isoformat(),
			'updated_at': req.updated_at.isoformat(),
			'comment': req.comment,
			'total_amount': float(req.total_amount),
			'items': [{
				'id': item.id,
				'product': {
					'id': item.product.id,
					'name': item.product.name,
					'is_glass': item.product.is_glass,
				} if item.product else None,
				'quantity': item.quantity,
				'size': item.size,
				'color': item.color,
				'price': float(item.price),
				'glass_type': item.glass_type,
				'paint_type': item.paint_type,
				'paint_color': item.paint_color,
				'cnc_specs': item.cnc_specs,
				'cutting_specs': item.cutting_specs,
				'packaging_notes': item.packaging_notes,
			} for item in req.items.all()],
			'order_id': req.order.id if req.order else None,
		})
	return JsonResponse(data, safe=False)


@login_required
def create_request(request):
	"""API: создание заявки"""
	if request.method != 'POST':
		return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
	
	try:
		data = json.loads(request.body)
		name = data.get('name')
		client_id = data.get('client_id')
		items_data = data.get('items_data', [])
		comment = data.get('comment', '')
		
		if not name or not client_id or not items_data:
			return JsonResponse({
				'error': 'Необходимо указать название заявки, клиента и товары'
			}, status=400)
		
		from apps.clients.models import Client
		client = get_object_or_404(Client, pk=client_id)
		
		# Создаем заявку
		request_obj = Request.objects.create(
			name=name,
			client=client,
			comment=comment,
			status='pending'
		)
		
		# Создаем позиции заявки
		total_amount = 0
		for item_data in items_data:
			product_id = item_data.get('product_id')
			quantity = item_data.get('quantity', 1)
			size = item_data.get('size', '')
			color = item_data.get('color', '')
			glass_type = item_data.get('glass_type', '')
			paint_type = item_data.get('paint_type', '')
			paint_color = item_data.get('paint_color', '')
			cnc_specs = item_data.get('cnc_specs', '')
			cutting_specs = item_data.get('cutting_specs', '')
			preparation_specs = item_data.get('preparation_specs', '')
			packaging_notes = item_data.get('packaging_notes', '')
			price = item_data.get('price', 0)
			
			from apps.products.models import Product
			product = get_object_or_404(Product, pk=product_id)
			
			RequestItem.objects.create(
				request=request_obj,
				product=product,
				quantity=quantity,
				size=size,
				color=color,
				glass_type=glass_type,
				paint_type=paint_type,
				paint_color=paint_color,
				cnc_specs=cnc_specs,
				cutting_specs=cutting_specs,
				preparation_specs=preparation_specs,
				packaging_notes=packaging_notes,
				price=price
			)
			
			total_amount += float(price) * quantity
		
		# Обновляем общую сумму
		request_obj.total_amount = total_amount
		request_obj.save()
		
		return JsonResponse({
			'id': request_obj.id,
			'name': request_obj.name,
			'status': request_obj.status,
			'message': 'Заявка успешно создана'
		}, status=201)
		
	except Exception as e:
		return JsonResponse({
			'error': f'Ошибка создания заявки: {str(e)}'
		}, status=500)
