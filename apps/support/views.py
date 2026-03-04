from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q
import json
import logging
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SupportChat, ChatMessage, AIUserSettings, SupportCategory, SupportTicket
from .serializers import (
    SupportChatSerializer, ChatMessageSerializer, AIUserSettingsSerializer,
    SupportTicketSerializer, CreateChatSerializer, SendMessageSerializer
)
from .ai_service import AISupportService

logger = logging.getLogger(__name__)

# Web Views
def support_landing(request):
    return render(request, 'support/landing.html')

@login_required
def support_dashboard(request):
    """Главная страница поддержки"""
    user_chats = SupportChat.objects.filter(user=request.user, is_active=True)
    ai_service = AISupportService()
    ai_available = ai_service.is_available()
    ai_enabled = ai_service.is_ai_enabled_for_user(request.user)
    
    # Добавляем last_message и message_count для каждого чата
    for chat in user_chats:
        chat.last_message = chat.messages.last()
        chat.message_count = chat.messages.count()
    
    context = {
        'chats': user_chats,
        'ai_available': ai_available,
        'ai_enabled': ai_enabled,
    }
    return render(request, 'support/dashboard.html', context)

@login_required
def chat_detail(request, chat_id):
    """Детальная страница чата"""
    chat = get_object_or_404(SupportChat, id=chat_id, user=request.user)
    messages = chat.messages.all().order_by('created_at')
    
    # Добавляем информацию о статусе ИИ
    ai_service = AISupportService()
    ai_enabled = ai_service.is_ai_enabled_for_user(request.user)
    
    context = {
        'chat': chat,
        'messages': messages,
        'ai_enabled': ai_enabled,
    }
    return render(request, 'support/chat_detail.html', context)

@login_required
def create_chat(request):
    """Создание нового чата"""
    if request.method == 'POST':
        title = request.POST.get('title', '')
        chat = SupportChat.objects.create(
            user=request.user,
            title=title or f"Чат {request.user.username}"
        )
        return JsonResponse({'success': True, 'chat_id': chat.id})
    
    # Добавляем информацию о статусе ИИ
    ai_service = AISupportService()
    ai_available = ai_service.is_available()
    ai_enabled = ai_service.is_ai_enabled_for_user(request.user)
    
    context = {
        'ai_available': ai_available,
        'ai_enabled': ai_enabled,
    }
    
    return render(request, 'support/create_chat.html', context)

# API Views
class ChatListAPIView(APIView):
    """API для получения списка чатов пользователя"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        chats = SupportChat.objects.filter(user=request.user, is_active=True)
        serializer = SupportChatSerializer(chats, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Создание нового чата"""
        serializer = CreateChatSerializer(data=request.data)
        if serializer.is_valid():
            chat = SupportChat.objects.create(
                user=request.user,
                title=serializer.validated_data.get('title', f"Чат {request.user.username}")
            )
            
            # Создаем тикет для администраторов
            SupportTicket.objects.create(chat=chat)
            
            return Response(SupportChatSerializer(chat).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChatDetailAPIView(APIView):
    """API для работы с конкретным чатом"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, chat_id):
        """Получение информации о чате и сообщений"""
        try:
            chat = SupportChat.objects.get(id=chat_id, user=request.user)
            serializer = SupportChatSerializer(chat)
            return Response(serializer.data)
        except SupportChat.DoesNotExist:
            return Response({'error': 'Чат не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request, chat_id):
        """Отправка сообщения в чат"""
        try:
            chat = SupportChat.objects.get(id=chat_id, user=request.user)
        except SupportChat.DoesNotExist:
            return Response({'error': 'Чат не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = SendMessageSerializer(data=request.data)
        if serializer.is_valid():
            content = serializer.validated_data['content']
            
            # Создаем сообщение пользователя
            user_message = ChatMessage.objects.create(
                chat=chat,
                message_type='user',
                content=content
            )
            
            # Обновляем время чата
            chat.updated_at = timezone.now()
            chat.save()
            
            # Генерируем ответ ИИ
            ai_service = AISupportService()
            if ai_service.is_available() and ai_service.is_ai_enabled_for_user(request.user):
                ai_response = ai_service.generate_ai_response(request.user, chat, content)
                ai_message = ai_service.create_ai_message(chat, ai_response)
                
                return Response({
                    'user_message': ChatMessageSerializer(user_message).data,
                    'ai_message': ChatMessageSerializer(ai_message).data if ai_message else None
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'user_message': ChatMessageSerializer(user_message).data,
                'ai_message': None
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AIStatusAPIView(APIView):
    """API для проверки статуса ИИ"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получение статуса ИИ для пользователя"""
        ai_service = AISupportService()
        ai_available = ai_service.is_available()
        ai_enabled = ai_service.is_ai_enabled_for_user(request.user)
        
        return Response({
            'ai_available': ai_available,
            'ai_enabled': ai_enabled,
        })

# Admin Views
class AdminSupportDashboard(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Дашборд поддержки для администраторов"""
    model = SupportTicket
    template_name = 'support/admin_dashboard.html'
    context_object_name = 'tickets'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        return SupportTicket.objects.select_related('chat__user', 'category', 'assigned_admin').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_tickets'] = SupportTicket.objects.count()
        context['open_tickets'] = SupportTicket.objects.filter(status='open').count()
        context['urgent_tickets'] = SupportTicket.objects.filter(priority='urgent').count()
        return context

class AdminChatDetail(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Детальная страница чата для администраторов"""
    model = SupportChat
    template_name = 'support/admin_chat_detail.html'
    context_object_name = 'chat'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['messages'] = self.object.messages.all().order_by('created_at')
        context['ticket'] = getattr(self.object, 'ticket', None)
        
        # Добавляем информацию о статусе ИИ
        ai_service = AISupportService()
        context['ai_enabled'] = ai_service.is_ai_enabled_for_user(self.object.user)
        
        # Добавляем список администраторов для назначения
        from django.contrib.auth import get_user_model
        User = get_user_model()
        context['admins'] = User.objects.filter(is_staff=True)
        
        return context

# Admin API Views
class AdminToggleAIView(APIView):
    """API для администраторов по управлению ИИ пользователей"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        """Включение/отключение ИИ для пользователя"""
        if not request.user.is_staff:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        enabled = request.data.get('enabled', True)
        ai_service = AISupportService()
        
        if ai_service.toggle_ai_for_user(target_user, enabled):
            return Response({
                'success': True,
                'message': f'ИИ {"включен" if enabled else "отключен"} для пользователя {target_user.username}'
            })
        else:
            return Response({
                'success': False,
                'message': 'Ошибка изменения настроек ИИ'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminSendMessageView(APIView):
    """API для администраторов по отправке сообщений в чат"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, chat_id):
        """Отправка сообщения от администратора"""
        if not request.user.is_staff:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            chat = SupportChat.objects.get(id=chat_id)
        except SupportChat.DoesNotExist:
            return Response({'error': 'Чат не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        content = request.data.get('content', '')
        if not content:
            return Response({'error': 'Содержание сообщения обязательно'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Создаем сообщение администратора
        admin_message = ChatMessage.objects.create(
            chat=chat,
            message_type='admin',
            content=content
        )
        
        # Обновляем время чата
        chat.updated_at = timezone.now()
        chat.save()
        
        return Response(ChatMessageSerializer(admin_message).data, status=status.HTTP_201_CREATED)
