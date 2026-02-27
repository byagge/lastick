from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Главная страница
    path('', views.finance_dashboard, name='dashboard'),
    
    # Категории расходов
    path('expense-categories/', views.expense_categories, name='expense_categories'),
    path('expense-categories/create/', views.expense_category_create, name='expense_category_create'),
    path('expense-categories/<int:pk>/edit/', views.expense_category_edit, name='expense_category_edit'),
    path('expense-categories/<int:pk>/delete/', views.expense_category_delete, name='expense_category_delete'),
    
    # Поставщики
    path('suppliers/', views.suppliers, name='suppliers'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    
    # Товары поставщиков
    path('supplier-items/', views.supplier_items, name='supplier_items'),
    path('supplier-items/create/', views.supplier_item_create, name='supplier_item_create'),
    path('supplier-items/<int:pk>/details/', views.supplier_item_details, name='supplier_item_details'),
    path('supplier-items/<int:pk>/edit/', views.supplier_item_edit, name='supplier_item_edit'),
    path('supplier-items/<int:pk>/delete/', views.supplier_item_delete, name='supplier_item_delete'),
    
    # Движение денег
    path('money-movements/', views.money_movements, name='money_movements'),
    path('money-movements/create/', views.money_movement_create, name='money_movement_create'),
    path('money-movements/<int:pk>/details/', views.money_movement_details, name='money_movement_details'),
    
    # Расходы
    path('expenses/', views.expenses, name='expenses'),
    path('expenses/mobile/', views.expenses_mobile, name='expenses_mobile'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/details/', views.expense_details, name='expense_details'),
    
    # Доходы
    path('incomes/', views.incomes, name='incomes'),
    path('incomes/create/', views.income_create, name='income_create'),
    path('incomes/<int:pk>/details/', views.income_details, name='income_details'),
    
    # Имущество завода
    path('factory-assets/', views.factory_assets, name='factory_assets'),
    path('factory-assets/create/', views.factory_asset_create, name='factory_asset_create'),
    path('factory-assets/<int:pk>/', views.factory_asset_detail, name='factory_asset_detail'),
    path('factory-assets/<int:pk>/edit/', views.factory_asset_edit, name='factory_asset_edit'),
    path('factory-assets/<int:pk>/delete/', views.factory_asset_delete, name='factory_asset_delete'),
    
    # Финансовые отчеты
    path('financial-reports/', views.financial_reports, name='financial_reports'),
    path('financial-reports/create/', views.financial_report_create, name='financial_report_create'),
    path('financial-reports/<int:pk>/', views.financial_report_detail, name='financial_report_detail'),
    path('financial-reports/<int:pk>/edit/', views.financial_report_edit, name='financial_report_edit'),
    path('financial-reports/<int:pk>/delete/', views.financial_report_delete, name='financial_report_delete'),
    path('financial-reports/<int:pk>/export/csv/', views.financial_report_export_csv, name='financial_report_export_csv'),
    path('financial-reports/<int:pk>/export/excel/', views.financial_report_export_excel, name='financial_report_export_excel'),
    
    # API для AJAX
    path('api/expense-categories/', views.get_expense_categories, name='api_expense_categories'),
    path('api/suppliers/', views.get_suppliers, name='api_suppliers'),
    path('api/dashboard-stats/', views.dashboard_stats, name='api_dashboard_stats'),

    # Долги
    path('debts/', views.debts, name='debts'),
    path('debts/create/', views.debt_create, name='debt_create'),
    path('debts/<int:pk>/', views.debt_detail, name='debt_detail'),
    path('debts/<int:pk>/add-payment/', views.debt_add_payment, name='debt_add_payment'),
    path('debts/<int:pk>/delete/', views.debt_delete, name='debt_delete'),

    # Бухгалтерия (двойная запись)
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('journal/', views.journal_entries, name='journal_entries'),
    path('journal/create/', views.journal_entry_create, name='journal_entry_create'),
    path('journal/<uuid:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('journal/<uuid:pk>/add-line/', views.journal_entry_add_line, name='journal_entry_add_line'),
    path('journal/export/<str:format>/', views.journal_entry_export, name='journal_entry_export'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    
    # Расширенная бухгалтерия
    path('analytical-accounts/', views.analytical_accounts, name='analytical_accounts'),
    path('analytical-accounts/create/', views.analytical_account_create, name='analytical_account_create'),
    path('analytical-accounts/<int:pk>/edit/', views.analytical_account_edit, name='analytical_account_edit'),
    path('standard-operations/', views.standard_operations, name='standard_operations'),
    path('standard-operations/create/', views.standard_operation_create, name='standard_operation_create'),
    path('standard-operations/<int:pk>/', views.standard_operation_detail, name='standard_operation_detail'),
    path('standard-operations/<int:pk>/edit/', views.standard_operation_edit, name='standard_operation_edit'),
    path('correspondences/', views.account_correspondences, name='account_correspondences'),
    path('correspondences/create/', views.account_correspondence_create, name='account_correspondence_create'),
    path('correspondences/<int:pk>/edit/', views.account_correspondence_edit, name='account_correspondence_edit'),
    path('financial-periods/', views.financial_periods, name='financial_periods'),
    path('financial-periods/create/', views.financial_period_create, name='financial_period_create'),
    path('financial-periods/<int:pk>/close/', views.financial_period_close, name='financial_period_close'),
    path('financial-periods/<int:pk>/edit/', views.financial_period_edit, name='financial_period_edit'),
    
    # Заявки
    path('requests/', views.requests_list, name='requests'),
    path('requests/create/', views.request_create, name='request_create'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/edit/', views.request_edit, name='request_edit'),
    path('requests/<int:pk>/delete/', views.request_delete, name='request_delete'),
    
    # API для заявок
    path('api/requests/', views.get_requests, name='api_requests'),
    path('api/requests/create/', views.create_request, name='api_create_request'),
]
