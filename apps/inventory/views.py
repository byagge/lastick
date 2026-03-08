from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import transaction
import json
from decimal import Decimal
from django.db import models

from .models import (
    RawMaterial,
    MaterialIncoming,
    EmployeeMaterialBalance,
    MaterialIssueLog,
)
from apps.defects.models import DefectRework


def _as_float(value):
    if value is None:
        return 0.0
    return float(value)

def _fifo_batches(material):
    batches = []

    incomings = material.incomings.all().order_by('created_at', 'id')
    for incoming in incomings:
        unit_cost = incoming.price_per_unit
        if unit_cost is None:
            unit_cost = material.purchase_price or material.price or Decimal('0')
        batches.append({
            'quantity': Decimal(str(incoming.quantity or 0)),
            'price': Decimal(str(unit_cost or 0)),
            'created_at': incoming.created_at,
        })

    reworks = DefectRework.objects.filter(
        raw_material=material,
        workshop_id=4,
    ).order_by('created_at', 'id')
    rework_cost = material.purchase_price or material.price or Decimal('0')
    for rework in reworks:
        batches.append({
            'quantity': Decimal(str(rework.output_quantity or 0)),
            'price': Decimal(str(rework_cost or 0)),
            'created_at': rework.created_at,
        })

    batches.sort(key=lambda b: b.get('created_at'))

    issues = material.issue_logs.all().order_by('created_at', 'id')
    for issue in issues:
        remaining = Decimal(str(issue.quantity or 0))
        if remaining <= 0:
            continue
        for batch in batches:
            if remaining <= 0:
                break
            if batch['quantity'] <= 0:
                continue
            take = min(batch['quantity'], remaining)
            batch['quantity'] -= take
            remaining -= take

    if not batches and (material.quantity or 0) > 0:
        fallback_cost = material.purchase_price or material.price or Decimal('0')
        batches.append({
            'quantity': Decimal(str(material.quantity or 0)),
            'price': Decimal(str(fallback_cost)),
            'created_at': material.created_at,
        })

    return batches


def _material_value_from_batches(batches):
    total = Decimal('0')
    for batch in batches:
        qty = Decimal(str(batch['quantity'] or 0))
        price = Decimal(str(batch['price'] or 0))
        if qty <= 0:
            continue
        total += qty * price
    return total.quantize(Decimal('0.01'))

def is_mobile(request):
    """Определяет, является ли устройство мобильным"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    mobile_keywords = ['android', 'iphone', 'ipad', 'mobile', 'opera mini', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)

def materials_page(request):
    """Страница управления материалами"""
    template = 'materials_mobile.html' if is_mobile(request) else 'materials.html'
    return render(request, template)


def issue_page(request):
    return render(request, 'inventory_issue.html')

@csrf_exempt
@require_http_methods(["GET"])
def api_materials_list(request):
    """API для получения списка материалов"""
    try:
        materials = RawMaterial.objects.all().order_by('name', 'id')[:100]  # Ограничиваем количество
        materials_data = []

        for material in materials:
            batches = _fifo_batches(material)
            total_value = _material_value_from_batches(batches)
            materials_data.append({
                'id': material.id,
                'name': material.name,
                'unit': material.unit,
                'quantity': _as_float(material.quantity),
                'min_quantity': _as_float(material.min_quantity),
                'price': _as_float(material.price),
                'purchase_price': _as_float(material.purchase_price),
                'total_value': _as_float(total_value),
                'country': material.country,
                'description': material.description,
                'created_at': material.created_at.isoformat(),
                'updated_at': material.updated_at.isoformat()
            })

        return JsonResponse({
            'status': 'success',
            'data': materials_data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_material_create(request):
    """API для создания нового материала"""
    try:
        data = json.loads(request.body)
        
        # Валидация данных
        required_fields = ['name', 'unit', 'quantity', 'min_quantity', 'price']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Поле {field} обязательно для заполнения'
                }, status=400)
        
        # Создание материала
        material = RawMaterial.objects.create(
            name=data['name'],
            unit=data['unit'],
            quantity=Decimal(str(data['quantity'])),
            min_quantity=Decimal(str(data['min_quantity'])),
            price=Decimal(str(data['price'])),
            country=data.get('country', ''),
            description=data.get('description', '')
        )
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'id': material.id,
                'name': material.name,
                'unit': material.unit,
                'quantity': _as_float(material.quantity),
                'min_quantity': _as_float(material.min_quantity),
                'price': _as_float(material.price),
                'purchase_price': _as_float(material.purchase_price),
                'total_value': _as_float(material.total_value),
                'country': material.country,
                'description': material.description,
                'created_at': material.created_at.isoformat(),
                'updated_at': material.updated_at.isoformat()
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Неверный формат JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
def api_material_update(request, material_id):
    """API для обновления материала"""
    try:
        data = json.loads(request.body)
        
        try:
            material = RawMaterial.objects.get(id=material_id)
        except RawMaterial.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Материал не найден'
            }, status=404)
        
        # Обновление полей
        if 'name' in data:
            material.name = data['name']
        if 'unit' in data:
            material.unit = data['unit']
        if 'quantity' in data:
            material.quantity = Decimal(str(data['quantity']))
        if 'min_quantity' in data:
            material.min_quantity = Decimal(str(data['min_quantity']))
        if 'price' in data:
            material.price = Decimal(str(data['price']))
        if 'country' in data:
            material.country = data['country']
        if 'description' in data:
            material.description = data['description']
        
        # Сохраняем изменения
        material.save()
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'id': material.id,
                'name': material.name,
                'unit': material.unit,
                'quantity': _as_float(material.quantity),
                'min_quantity': _as_float(material.min_quantity),
                'price': _as_float(material.price),
                'purchase_price': _as_float(material.purchase_price),
                'total_value': _as_float(material.total_value),
                'country': material.country,
                'description': material.description,
                'created_at': material.created_at.isoformat(),
                'updated_at': material.updated_at.isoformat()
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Неверный формат JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def api_material_delete(request, material_id):
    """API для удаления материала"""
    try:
        try:
            material = RawMaterial.objects.get(id=material_id)
        except RawMaterial.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Материал не найден'
            }, status=404)
        
        material.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Материал успешно удален'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_materials_bulk_delete(request):
    """API для массового удаления материалов"""
    try:
        data = json.loads(request.body)
        material_ids = data.get('ids', [])
        
        if not material_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'Не указаны ID материалов для удаления'
            }, status=400)
        
        deleted_count = RawMaterial.objects.filter(id__in=material_ids).delete()[0]
        
        return JsonResponse({
            'status': 'success',
            'message': f'Удалено {deleted_count} материалов'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Неверный формат JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def api_materials_stats(request):
    """API для получения статистики материалов"""
    try:
        materials = RawMaterial.objects.all()
        
        total_value = Decimal('0')
        for material in materials:
            batches = _fifo_batches(material)
            total_value += _material_value_from_batches(batches)
        total_items = materials.count()
        low_stock_count = materials.filter(quantity__lte=models.F('min_quantity')).count()
        avg_base = sum(
            (material.purchase_price or material.price or 0)
            for material in materials
        )
        avg_price = avg_base / total_items if total_items else 0
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'totalValue': _as_float(total_value),
                'totalItems': total_items,
                'lowStockCount': low_stock_count,
                'avgPrice': _as_float(avg_price)
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_material_incoming(request):
    """API для добавления прихода материала"""
    try:
        data = json.loads(request.body)
        
        # Валидация данных
        required_fields = ['material_id', 'quantity']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Поле {field} обязательно для заполнения'
                }, status=400)
        
        try:
            material = RawMaterial.objects.get(id=data['material_id'])
        except RawMaterial.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Материал не найден'
            }, status=404)
        
        # Создание записи прихода
        price_per_unit = data.get('price_per_unit')
        if price_per_unit is not None and price_per_unit != '':
            price_per_unit = Decimal(str(price_per_unit))
        else:
            price_per_unit = None
            
        incoming = MaterialIncoming.objects.create(
            material=material,
            quantity=Decimal(str(data['quantity'])),
            price_per_unit=price_per_unit,
            notes=data.get('notes')  # Теперь может быть None
        )

        # Обновление средней цены и количества материала (метод средневзвешенной)
        old_qty = material.quantity or Decimal('0')
        old_cost = material.purchase_price or material.price or Decimal('0')
        new_qty = incoming.quantity or Decimal('0')

        if incoming.price_per_unit is not None:
            new_cost = incoming.price_per_unit
            total_qty = old_qty + new_qty
            if total_qty > 0:
                total_value = old_qty * old_cost + new_qty * new_cost
                material.purchase_price = (total_value / total_qty).quantize(Decimal('0.01'))

        material.quantity = old_qty + new_qty
        material.save()
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'id': incoming.id,
                'material_name': material.name,
                'quantity': _as_float(incoming.quantity),
                'price_per_unit': _as_float(incoming.price_per_unit) if incoming.price_per_unit else None,
                'total_value': _as_float(incoming.total_value) if incoming.total_value else None,
                'notes': incoming.notes,
                'created_at': incoming.created_at.isoformat(),
                'new_quantity': _as_float(material.quantity)
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Неверный формат JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def api_material_incomings(request, material_id):
    """API для получения истории приходов материала"""
    try:
        try:
            material = RawMaterial.objects.get(id=material_id)
        except RawMaterial.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Материал не найден'
            }, status=404)
        
        incomings = material.incomings.all()
        incomings_data = []
        
        for incoming in incomings:
            incomings_data.append({
                'id': incoming.id,
                'quantity': _as_float(incoming.quantity),
                'price_per_unit': _as_float(incoming.price_per_unit) if incoming.price_per_unit else None,
                'total_value': _as_float(incoming.total_value) if incoming.total_value else None,
                'notes': incoming.notes,
                'created_at': incoming.created_at.isoformat()
            })
        
        return JsonResponse({
            'status': 'success',
            'data': incomings_data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500) 


@csrf_exempt
@require_http_methods(["GET"])
def api_material_reworks(request, material_id):
    """API: история приходов после обработки в цехе ID4."""
    try:
        try:
            material = RawMaterial.objects.get(id=material_id)
        except RawMaterial.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Материал не найден'
            }, status=404)

        reworks = DefectRework.objects.filter(
            raw_material=material,
            workshop_id=4,
        ).select_related('employee', 'workshop', 'defect')
        reworks_data = []

        for rework in reworks:
            if rework.employee:
                full_name = (
                    rework.employee.get_full_name()
                    if hasattr(rework.employee, "get_full_name")
                    else ""
                )
                username = getattr(rework.employee, "username", "") or ""
                employee_name = full_name or username or str(rework.employee_id)
            else:
                employee_name = ""

            reworks_data.append({
                'id': rework.id,
                'defect_id': rework.defect_id,
                'input_quantity': _as_float(rework.input_quantity),
                'output_quantity': _as_float(rework.output_quantity),
                'comment': rework.comment,
                'employee_name': employee_name,
                'workshop_name': rework.workshop.name if rework.workshop else '',
                'created_at': rework.created_at.isoformat(),
            })

        return JsonResponse({
            'status': 'success',
            'data': reworks_data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_material_price_breakdown(request, material_id):
    """API: текущие остатки по ценам закупки (FIFO)."""
    try:
        try:
            material = RawMaterial.objects.get(id=material_id)
        except RawMaterial.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Материал не найден'
            }, status=404)

        batches = _fifo_batches(material)
        totals = {}
        total_quantity = Decimal('0')
        total_value = _material_value_from_batches(batches)
        for batch in batches:
            if batch['quantity'] <= 0:
                continue
            price = Decimal(str(batch['price'] or 0)).quantize(Decimal('0.01'))
            qty = Decimal(str(batch['quantity'] or 0))
            totals[price] = totals.get(price, Decimal('0')) + qty
            total_quantity += qty

        breakdown = [
            {'price': _as_float(price), 'quantity': _as_float(qty)}
            for price, qty in sorted(totals.items(), key=lambda item: item[0])
        ]

        return JsonResponse({
            'status': 'success',
            'data': {
                'breakdown': breakdown,
                'total_quantity': _as_float(total_quantity),
                'total_value': _as_float(total_value),
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_material_issue(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Требуется авторизация'
        }, status=403)

    try:
        data = json.loads(request.body)
        material_id = data.get('material_id')
        quantity = data.get('quantity')

        if not material_id or quantity is None:
            return JsonResponse({
                'status': 'error',
                'message': 'material_id и quantity обязательны'
            }, status=400)

        quantity = Decimal(str(quantity))
        if quantity <= 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Количество должно быть больше нуля'
            }, status=400)

        with transaction.atomic():
            try:
                material = RawMaterial.objects.select_for_update().get(id=material_id)
            except RawMaterial.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Материал не найден'
                }, status=404)

            if material.quantity < quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Недостаточно материалов на складе'
                }, status=400)

            quantity_before = material.quantity
            material.quantity -= quantity
            material.save()

            balance, _ = EmployeeMaterialBalance.objects.select_for_update().get_or_create(
                employee=request.user,
                material=material,
                defaults={'quantity': 0}
            )
            balance.quantity += quantity
            balance.save()

            MaterialIssueLog.objects.create(
                material=material,
                employee=request.user,
                quantity=quantity,
                quantity_before=quantity_before,
                quantity_after=material.quantity,
                source='issue_page',
            )

        return JsonResponse({
            'status': 'success',
            'data': {
                'material_id': material.id,
                'material_quantity': _as_float(material.quantity),
                'balance_quantity': _as_float(balance.quantity),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Некорректный JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_material_balances(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Требуется авторизация'
        }, status=403)

    try:
        balances = EmployeeMaterialBalance.objects.filter(employee=request.user).select_related('material')
        data = []
        for balance in balances:
            data.append({
                'material_id': balance.material_id,
                'material_name': balance.material.name,
                'unit': balance.material.unit,
                'quantity': _as_float(balance.quantity),
                'updated_at': balance.updated_at.isoformat(),
            })
        return JsonResponse({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_material_issues(request, material_id):
    """API: история выдач конкретного материала для админских экранов."""
    if not request.user.is_authenticated:
        return JsonResponse(
            {'status': 'error', 'message': 'Требуется авторизация'},
            status=403,
        )

    try:
        try:
            material = RawMaterial.objects.get(id=material_id)
        except RawMaterial.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Материал не найден'},
                status=404,
            )

        logs = material.issue_logs.select_related('employee').all()
        data = []
        for log in logs:
            if log.employee:
                full_name = (
                    log.employee.get_full_name()
                    if hasattr(log.employee, "get_full_name")
                    else ""
                )
                username = getattr(log.employee, "username", "") or ""
                employee_name = full_name or username or str(log.employee_id)
            else:
                employee_name = ""

            data.append({
                'id': log.id,
                'employee_id': log.employee_id,
                'employee_name': employee_name,
                'quantity': _as_float(log.quantity),
                'quantity_before': _as_float(log.quantity_before),
                'quantity_after': _as_float(log.quantity_after),
                'source': log.source,
                'created_at': log.created_at.isoformat(),
            })

        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=500,
        )
