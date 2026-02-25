from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from .models import Defect
from .serializers import DefectSerializer, DefectConfirmationSerializer, DefectRepairSerializer, DefectListSerializer
from apps.operations.workshops.models import Workshop
from core.utils import is_mobile_device

def defects_page(request):
    """Страница списка браков с автоматическим определением устройства"""
    # if is_mobile_device(request):
    #     return render(request, 'defects_mobile.html')
    return render(request, 'defects.html')

def defects_mobile_page(request):
    """Мобильная страница списка браков (для прямого доступа)"""
    return render(request, 'defects_mobile.html')

class DefectViewSet(viewsets.ModelViewSet):
    queryset = Defect.objects.select_related(
        'product', 'user', 'confirmed_by', 'target_workshop', 'employee_task'
    ).prefetch_related('employee_task__stage__workshop').all()
    serializer_class = DefectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтрация по статусу
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Фильтрация по цеху (браки сотрудников из определенного цеха)
        workshop_filter = self.request.query_params.get('workshop')
        if workshop_filter:
            queryset = queryset.filter(user__workshop_id=workshop_filter)
        
        # Фильтрация по продукту
        product_filter = self.request.query_params.get('product')
        if product_filter:
            queryset = queryset.filter(product_id=product_filter)
        
        # Фильтрация по сотруднику
        user_filter = self.request.query_params.get('user')
        if user_filter:
            queryset = queryset.filter(user_id=user_filter)
        
        return queryset.order_by('-created_at')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def defects_list(request):
    """Список браков для API"""
    try:
        defects = Defect.objects.all().select_related('user', 'employee_task', 'target_workshop')
        serializer = DefectListSerializer(defects, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_defect(request, defect_id):
    """Подтверждение брака мастером"""
    try:
        defect = Defect.objects.get(id=defect_id)
        
        # Проверяем права мастера
        if not defect.can_be_confirmed_by(request.user):
            return Response(
                {'error': 'У вас нет прав для подтверждения этого брака'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что брак еще не подтвержден
        if defect.status != 'pending':
            return Response(
                {'error': 'Брак уже подтвержден или обработан'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DefectConfirmationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            try:
                defect.confirm_defect(
                    master=request.user,
                    is_repairable=data['is_repairable'],
                    defect_type=data.get('defect_type'),
                    target_workshop=data.get('target_workshop_id'),
                    comment=data.get('comment', ''),
                    penalty_amount=data.get('penalty_amount')
                )
                
                return Response({
                    'success': True,
                    'message': 'Брак успешно подтвержден',
                    'defect': DefectSerializer(defect).data
                })
                
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Defect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_defect_repaired(request, defect_id):
    """Отметить брак как починенный"""
    try:
        defect = Defect.objects.get(id=defect_id)
        
        # Проверяем, что брак можно починить
        if defect.status not in ['repairable', 'transferred']:
            return Response(
                {'error': 'Брак нельзя отметить как починенный'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        comment = request.data.get('comment', '')
        defect.mark_as_repaired(comment)
        
        return Response({
            'success': True,
            'message': 'Брак отмечен как починенный',
            'defect': DefectSerializer(defect).data
        })
        
    except Defect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_defect(request, defect_id):
    """Закрыть брак"""
    try:
        defect = Defect.objects.get(id=defect_id)
        
        # Проверяем права (только админы и мастера)
        if request.user.role != 'admin':
            return Response(
                {'error': 'У вас нет прав для закрытия брака'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что брак починен
        if defect.status != 'repaired':
            return Response(
                {'error': 'Можно закрыть только починенный брак'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        defect.close_defect()
        
        return Response({
            'success': True,
            'message': 'Брак закрыт',
            'defect': DefectSerializer(defect).data
        })
        
    except Defect.DoesNotExist:
        return Response({'error': 'Брак не найден'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def defects_stats(request):
    """Статистика браков"""
    try:
        # Общая статистика
        total_defects = Defect.objects.count()
        pending_confirmation = Defect.objects.filter(status='pending').count()
        repairable = Defect.objects.filter(status='repairable').count()
        repaired = Defect.objects.filter(status='repaired').count()
        irreparable = Defect.objects.filter(status='irreparable').count()
        closed = Defect.objects.filter(status='closed').count()
        
        # Статистика по типам браков
        technical_defects = Defect.objects.filter(defect_type='technical').count()
        manual_defects = Defect.objects.filter(defect_type='manual').count()
        
        # Статистика по цехам
        workshop_stats = Defect.objects.values('user__workshop__name').annotate(
            count=Count('id')
        ).filter(user__workshop__name__isnull=False)
        
        return Response({
            'total_defects': total_defects,
            'pending_confirmation': pending_confirmation,
            'repairable': repairable,
            'repaired': repaired,
            'irreparable': irreparable,
            'closed': closed,
            'technical_defects': technical_defects,
            'manual_defects': manual_defects,
            'workshop_stats': list(workshop_stats)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 