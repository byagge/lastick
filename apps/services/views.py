from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Service
from apps.operations.workshops.models import Workshop
from apps.inventory.models import RawMaterial
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg
import json
from .models import ServiceMaterial
import logging

logger = logging.getLogger(__name__)


def service_list(request):
    query = request.GET.get('q', '')
    services_qs = Service.objects.select_related('workshop').all().order_by('name', 'id')
    
    if query:
        services_qs = services_qs.filter(
            Q(name__icontains=query) | Q(code__icontains=query) | Q(description__icontains=query)
        )
    
    # Добавляем пагинацию
    paginator = Paginator(services_qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Определение мобильного устройства по User-Agent
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(mobile in user_agent for mobile in [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 
        'windows phone', 'opera mini', 'mobile safari'
    ])
    
    # Выбор шаблона в зависимости от устройства
    template = 'services_mobile.html' if is_mobile else 'services.html'
    
    return render(request, template, {
        'services': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.paginator.num_pages > 1,
        'query': query,
    })


def service_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        unit = request.POST.get('unit', 'услуга')
        price = request.POST.get('price', 0)
        is_active = request.POST.get('is_active', 'on') == 'on'
        Service.objects.create(
            name=name, code=code, description=description, unit=unit, price=price, is_active=is_active
        )
        return redirect('service_list')
    return render(request, 'service_form.html')


def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        service.name = request.POST.get('name')
        service.code = request.POST.get('code')
        service.description = request.POST.get('description', '')
        service.unit = request.POST.get('unit', 'услуга')
        service.price = request.POST.get('price', 0)
        service.is_active = request.POST.get('is_active', 'on') == 'on'
        service.save()
        return redirect('service_list')
    return render(request, 'service_form.html', {'service': service})


def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        service.delete()
        return redirect('service_list')
    return render(request, 'service_confirm_delete.html', {'service': service})


def service_duplicate(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        new_service = Service.objects.create(
            name=service.name + ' (копия)',
            code=service.code + '_copy',
            description=service.description,
            unit=service.unit,
            is_active=service.is_active
        )
        return redirect('service_edit', pk=new_service.pk)
    return render(request, 'service_confirm_duplicate.html', {'service': service})


@csrf_exempt
def api_service_list(request):
    if request.method == 'GET':
        services = Service.objects.select_related('workshop').prefetch_related('service_materials__material').all()
        data = []
        for s in services:
            d = {
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'unit': s.unit,
                'workshop': s.workshop.id if s.workshop else None,
                'workshop_name': s.workshop.name if s.workshop else '',
                'service_price': float(s.service_price),
                'defect_penalty': float(s.defect_penalty),
                'is_active': s.is_active,
                'created_at': s.created_at,
                'updated_at': s.updated_at,
                'materials_info': [
                    {
                        'id': sm.material.id,
                        'name': str(sm.material),
                        'amount': float(sm.amount)
                    }
                    for sm in s.service_materials.all()
                ]
            }
            data.append(d)
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_create(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Преобразуем is_active в булево значение
        is_active = data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        else:
            is_active = bool(is_active)
            
        service = Service.objects.create(
            name=data.get('name',''),
            description=data.get('description',''),
            unit=data.get('unit','услуга'),
            workshop_id=data.get('workshop'),
            service_price=data.get('service_price',0),
            defect_penalty=data.get('defect_penalty',0),
            is_active=is_active
        )
        
        # Добавляем материалы к услуге
        materials_data = data.get('materials', [])
        for mat_data in materials_data:
            if mat_data.get('id') and mat_data.get('amount'):
                ServiceMaterial.objects.create(
                    service=service,
                    material_id=mat_data['id'],
                    amount=mat_data['amount']
                )
        
        # Создаем собственный словарь для ответа
        response_data = {
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'unit': service.unit,
            'workshop': service.workshop.id if service.workshop else None,
            'workshop_name': service.workshop.name if service.workshop else '',
            'service_price': float(service.service_price),
            'defect_penalty': float(service.defect_penalty),
            'is_active': service.is_active,
            'created_at': service.created_at.isoformat() if service.created_at else None,
            'updated_at': service.updated_at.isoformat() if service.updated_at else None,
            'materials_info': []
        }
        
        return JsonResponse({'status': 'success', 'data': response_data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_update(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'PUT':
        data = json.loads(request.body)
        
        # Обновляем основные поля
        fields_to_update = ['name', 'description', 'unit', 'workshop', 'service_price', 'defect_penalty', 'is_active']
        for field in fields_to_update:
            if field in data:
                if field == 'workshop':
                    service.workshop_id = data[field]
                elif field == 'is_active':
                    # Преобразуем строковое значение в булево
                    if isinstance(data[field], str):
                        service.is_active = data[field].lower() == 'true'
                    else:
                        service.is_active = bool(data[field])
                else:
                    setattr(service, field, data[field])
        
        service.save()
        
        # Обновляем материалы
        if 'materials' in data:
            # Удаляем старые связи с материалами
            service.service_materials.all().delete()
            
            # Добавляем новые материалы
            materials_data = data.get('materials', [])
            for mat_data in materials_data:
                if mat_data.get('id') and mat_data.get('amount'):
                    ServiceMaterial.objects.create(
                        service=service,
                        material_id=mat_data['id'],
                        amount=mat_data['amount']
                    )
        
        # Создаем собственный словарь для ответа
        response_data = {
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'unit': service.unit,
            'workshop': service.workshop.id if service.workshop else None,
            'workshop_name': service.workshop.name if service.workshop else '',
            'service_price': float(service.service_price),
            'defect_penalty': float(service.defect_penalty),
            'is_active': service.is_active,
            'created_at': service.created_at.isoformat() if service.created_at else None,
            'updated_at': service.updated_at.isoformat() if service.updated_at else None,
            'materials_info': [
                {
                    'id': sm.material.id,
                    'name': str(sm.material),
                    'amount': float(sm.amount)
                }
                for sm in service.service_materials.all()
            ]
        }
        
        return JsonResponse({'status': 'success', 'data': response_data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'DELETE':
        service.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_bulk_delete(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids',[])
        Service.objects.filter(id__in=ids).delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_stats(request):
    if request.method == 'GET':
        qs = Service.objects.all()
        totalValue = qs.aggregate(total=Sum('service_price'))['total'] or 0
        totalItems = qs.count()
        activeServices = qs.filter(is_active=True).count()
        avgPrice = qs.aggregate(avg=Avg('service_price'))['avg'] or 0
        return JsonResponse({'status': 'success', 'data': {
            'totalValue': totalValue,
            'totalItems': totalItems,
            'activeServices': activeServices,
            'avgPrice': avgPrice
        }})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_duplicate(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        # Преобразуем is_active в булево значение
        is_active = service.is_active
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        else:
            is_active = bool(is_active)
            
        new_service = Service.objects.create(
            name=service.name + ' (копия)',
            description=service.description,
            unit=service.unit,
            workshop=service.workshop,
            service_price=service.service_price,
            defect_penalty=service.defect_penalty,
            is_active=is_active
        )
        
        # Копируем материалы
        for sm in service.service_materials.all():
            ServiceMaterial.objects.create(
                service=new_service,
                material=sm.material,
                amount=sm.amount
            )
        
        # Создаем собственный словарь для ответа
        response_data = {
            'id': new_service.id,
            'name': new_service.name,
            'description': new_service.description,
            'unit': new_service.unit,
            'workshop': new_service.workshop.id if new_service.workshop else None,
            'workshop_name': new_service.workshop.name if new_service.workshop else '',
            'service_price': float(new_service.service_price),
            'defect_penalty': float(new_service.defect_penalty),
            'is_active': new_service.is_active,
            'created_at': new_service.created_at.isoformat() if new_service.created_at else None,
            'updated_at': new_service.updated_at.isoformat() if new_service.updated_at else None,
            'materials_info': [
                {
                    'id': sm.material.id,
                    'name': str(sm.material),
                    'amount': float(sm.amount)
                }
                for sm in new_service.service_materials.all()
            ]
        }
        
        return JsonResponse({'status': 'success', 'data': response_data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_materials(request):
    if request.method == 'GET':
        materials = RawMaterial.objects.all()
        data = [
            {'id': m.id, 'name': str(m)} for m in materials
        ]
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_workshops(request):
    if request.method == 'GET':
        workshops = Workshop.objects.all()
        data = [{'id': w.id, 'name': w.name} for w in workshops]
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

# API для мастера - получение услуг по цеху
@login_required
@csrf_exempt
def api_master_services(request):
    if request.method == 'GET':
        # Проверяем, что пользователь является мастером
        if not hasattr(request.user, 'role') or request.user.role not in ['admin']:
            logger.debug("User role '%s' is not allowed", getattr(request.user, 'role', 'No role'))
            return JsonResponse({'status': 'error', 'message': 'Access denied. Only masters can access this API.'}, status=403)
        
        workshop_id = request.GET.get('workshop')
        if not workshop_id:
            return JsonResponse({'status': 'error', 'message': 'Workshop ID required'}, status=400)
        
        # Проверяем, имеет ли мастер доступ к этому цеху
        user_workshops = []
        if request.user.is_authenticated:
            # 1. Цех, в котором работает пользователь
            if hasattr(request.user, 'workshop') and request.user.workshop:
                user_workshops.append(request.user.workshop.id)
            
            # 2. Цехи, которыми управляет пользователь как главный мастер
            managed_workshops = Workshop.objects.filter(manager=request.user, is_active=True)
            user_workshops.extend([w.id for w in managed_workshops])
            
            # 3. Дополнительные цехи, где пользователь является мастером
            try:
                from apps.operations.workshops.models import WorkshopMaster
                additional_workshops = WorkshopMaster.objects.filter(
                    master=request.user, 
                    is_active=True,
                    workshop__is_active=True
                ).select_related('workshop')
                user_workshops.extend([wm.workshop.id for wm in additional_workshops])
            except ImportError:
                pass
        
        # Проверяем доступ к запрашиваемому цеху
        if int(workshop_id) not in user_workshops:
            return JsonResponse({'status': 'error', 'message': 'Access denied to this workshop'}, status=403)
        
        services = Service.objects.filter(
            workshop_id=workshop_id,
            is_active=True
        ).select_related('workshop').prefetch_related('service_materials__material').order_by('name')
        
        data = []
        for service in services:
            service_data = {
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'unit': service.unit,
                'workshop': service.workshop.id if service.workshop else None,
                'workshop_name': service.workshop.name if service.workshop else '',
                'service_price': float(service.service_price),
                'defect_penalty': float(service.defect_penalty),
                'is_active': service.is_active,
                'created_at': service.created_at.isoformat() if service.created_at else None,
                'updated_at': service.updated_at.isoformat() if service.updated_at else None,
                'materials_info': [
                    {
                        'id': sm.material.id,
                        'name': str(sm.material),
                        'amount': float(sm.amount)
                    }
                    for sm in service.service_materials.all()
                ]
            }
            data.append(service_data)
        
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

# API для мастера - обновление цены услуги
@login_required
@csrf_exempt
def api_master_update_price(request, pk):
    if request.method == 'PATCH':
        # Проверяем, что пользователь является мастером
        if not hasattr(request.user, 'role') or request.user.role not in ['admin']:
            logger.debug("User role '%s' is not allowed", getattr(request.user, 'role', 'No role'))
            return JsonResponse({'status': 'error', 'message': 'Access denied. Only masters can access this API.'}, status=403)
        
        try:
            data = json.loads(request.body)
            service = get_object_or_404(Service, pk=pk)
            
            # Проверяем, имеет ли мастер доступ к цеху этой услуги
            user_workshops = []
            if request.user.is_authenticated:
                # 1. Цех, в котором работает пользователь
                if hasattr(request.user, 'workshop') and request.user.workshop:
                    user_workshops.append(request.user.workshop.id)
                
                # 2. Цехи, которыми управляет пользователь как главный мастер
                managed_workshops = Workshop.objects.filter(manager=request.user, is_active=True)
                user_workshops.extend([w.id for w in managed_workshops])
                
                # 3. Дополнительные цехи, где пользователь является мастером
                try:
                    from apps.operations.workshops.models import WorkshopMaster
                    additional_workshops = WorkshopMaster.objects.filter(
                        master=request.user, 
                        is_active=True,
                        workshop__is_active=True
                    ).select_related('workshop')
                    user_workshops.extend([wm.workshop.id for wm in additional_workshops])
                except ImportError:
                    pass
            
            # Проверяем доступ к цеху услуги
            if service.workshop and service.workshop.id not in user_workshops:
                return JsonResponse({'status': 'error', 'message': 'Access denied to modify this service'}, status=403)
            
            # Обновляем только цену услуги
            if 'service_price' in data:
                service.service_price = data['service_price']
                service.save()
            
            response_data = {
                'id': service.id,
                'name': service.name,
                'service_price': float(service.service_price),
                'updated_at': service.updated_at.isoformat() if service.updated_at else None,
            }
            
            return JsonResponse({'status': 'success', 'data': response_data})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

# API для мастера - получение цехов мастера
@login_required
@csrf_exempt
def api_master_workshops(request):
    if request.method == 'GET':
        # Проверяем, что пользователь является мастером
        if not hasattr(request.user, 'role') or request.user.role not in ['admin']:
            logger.debug("User role '%s' is not allowed", getattr(request.user, 'role', 'No role'))
            return JsonResponse({'status': 'error', 'message': 'Access denied. Only masters can access this API.'}, status=403)
        
        # Получаем только цехи текущего мастера
        user_workshops = []
        
        logger.debug("User authenticated: %s", request.user.is_authenticated)
        logger.debug("User: %s", request.user.username if request.user.is_authenticated else 'Anonymous')
        logger.debug("User role: %s", getattr(request.user, 'role', 'No role') if request.user.is_authenticated else 'No role')
        
        if request.user.is_authenticated:
            # 1. Цех, в котором работает пользователь
            if hasattr(request.user, 'workshop') and request.user.workshop:
                user_workshops.append(request.user.workshop)
                logger.debug("User workshop: %s (ID: %s)", request.user.workshop.name, request.user.workshop.id)
            else:
                logger.debug("User has no workshop assigned")
            
            # 2. Цехи, которыми управляет пользователь как главный мастер
            managed_workshops = Workshop.objects.filter(manager=request.user, is_active=True)
            logger.debug("Managed workshops count: %s", managed_workshops.count())
            for workshop in managed_workshops:
                if workshop not in user_workshops:
                    user_workshops.append(workshop)
                    logger.debug("Managed workshop: %s (ID: %s)", workshop.name, workshop.id)
            
            # 3. Дополнительные цехи, где пользователь является мастером
            # (если есть модель WorkshopMaster)
            try:
                from apps.operations.workshops.models import WorkshopMaster
                additional_workshops = WorkshopMaster.objects.filter(
                    master=request.user, 
                    is_active=True,
                    workshop__is_active=True
                ).select_related('workshop')
                
                logger.debug("Additional workshops count: %s", additional_workshops.count())
                for workshop_master in additional_workshops:
                    if workshop_master.workshop not in user_workshops:
                        user_workshops.append(workshop_master.workshop)
                        logger.debug("Additional workshop: %s (ID: %s)", workshop_master.workshop.name, workshop_master.workshop.id)
            except ImportError:
                logger.debug("WorkshopMaster model not found")
                pass
        else:
            logger.debug("User not authenticated")
        
        logger.debug("Total workshops found: %s", len(user_workshops))
        
        # Если у пользователя нет цехов, возвращаем пустой список
        if not user_workshops:
            data = []
            logger.debug("No workshops found for user")
        else:
            # Убираем дубликаты по ID и сортируем по имени
            seen_ids = set()
            unique_workshops = []
            for workshop in user_workshops:
                if workshop.id not in seen_ids:
                    seen_ids.add(workshop.id)
                    unique_workshops.append(workshop)
            
            unique_workshops.sort(key=lambda x: x.name)
            data = [{'id': w.id, 'name': w.name} for w in unique_workshops]
            logger.debug("Final unique workshops: %s", [w.name for w in unique_workshops])
        
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

# Представление для страницы мастера
@login_required
def master_services(request):
    return render(request, 'services_master.html')
