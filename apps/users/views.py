from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.conf import settings
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from apps.users.models import User, UserSettings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from functools import wraps
import re

# Create your views here.

class LoginView(View):
    template_name = 'login.html'  # Обновляем путь к шаблону

    @method_decorator(csrf_protect)
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return render(request, self.template_name)

    @method_decorator(csrf_protect)
    def post(self, request):
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        if not identifier or not password:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Пожалуйста, заполните все поля'}, status=400)
            messages.error(request, 'Пожалуйста, заполните все поля.')
            return render(request, self.template_name)

        # Определяем, является ли идентификатор номером телефона или username
        user = None
        
        # Проверяем, является ли это номером телефона
        if re.match(r'^\+?[0-9\s\-\(\)]+$', identifier):
            # Это номер телефона
            phone = identifier.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
            
            # Приводим к формату +996XXXXXXXXX
            if phone.startswith('+'):
                phone_number = phone
            elif phone.startswith('996'):
                phone_number = f'+{phone}'
            else:
                phone_number = f'+996{phone}'
            
            try:
                user = User.objects.get(phone=phone_number)
            except User.DoesNotExist:
                pass
        else:
            # Это username
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                pass

        if user is None:
            error_message = 'Пользователь с таким идентификатором не найден.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_message}, status=400)
            messages.error(request, error_message)
            return render(request, self.template_name)

        # Проверяем пароль
        authenticated_user = authenticate(request, username=user.username, password=password)
        if authenticated_user is not None:
            login(request, authenticated_user)
            # Редиректим на основе роли пользователя
            redirect_url = self.get_redirect_url_by_role(authenticated_user.role)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect_url': redirect_url})
            return redirect(redirect_url)
        else:
            error_message = 'Неверный пароль.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_message}, status=400)
            messages.error(request, error_message)
            return render(request, self.template_name)

    def get_redirect_url_by_role(self, role):
        """
        Возвращает URL для редиректа на основе роли пользователя
        """
        if not role:
            return '/'
            
        role_redirects = {
            User.Role.ADMIN: '/dashboard/',  # ????????????? -> ???????
            User.Role.ACCOUNTANT: '/finance/',  # ????????? -> ???????
            User.Role.WORKER: '/employee_tasks/tasks/',  # ????????? -> ??????
        }
        
        return role_redirects.get(role, '/')

class LogoutView(View):
    """
    Представление для выхода пользователя из системы
    """
    
    def get(self, request):
        """
        Обрабатывает GET запрос для выхода пользователя
        """
        logout(request)
        messages.success(request, 'Вы успешно вышли из системы.')
        return redirect('login')
    
    def post(self, request):
        """
        Обрабатывает POST запрос для выхода пользователя
        """
        logout(request)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Вы успешно вышли из системы.'})
        messages.success(request, 'Вы успешно вышли из системы.')
        return redirect('login')

def _is_worker(user):
    return getattr(user, 'role', None) == User.Role.WORKER


def worker_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _is_worker(request.user):
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped


class IsWorker(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and _is_worker(request.user)


@method_decorator(login_required, name='dispatch')
@method_decorator(worker_required, name='dispatch')
class ProfileView(View):
    template_name = 'profile.html'
    
    @method_decorator(login_required)
    def get(self, request):
        """
        Отображает профиль пользователя
        """
        return render(request, self.template_name, {
            'user': request.user
        })

class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorker]

    def get(self, request):
        user = request.user
        data = {
            'id': user.id,
            'full_name': user.get_full_name(),
            'role': getattr(user, 'role', None),
            'email': user.email,
            'phone': getattr(user, 'phone', None),
        }
        # Если у пользователя есть бизнес (например, user.business), добавить его id и имя
        business = getattr(user, 'business', None)
        if business:
            data['business'] = {'id': business.id, 'name': str(business)}
        return Response(data)


class SettingsView(View):
    template_name = 'settings.html'

    def get(self, request):
        return render(request, self.template_name, {
            'user': request.user
        })


class UserSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)
        full_name = user.get_full_name() or user.username
        initials = ''.join([p[0] for p in full_name.split() if p])[:2].upper() or (user.username[:1].upper())
        data = {
            'profile': {
                'name': full_name,
                'role': getattr(user, 'role', ''),
                'initials': initials
            },
            'settings': {
                'pin_login': settings_obj.pin_login,
                'face_id': settings_obj.face_id
            }
        }
        return Response(data)

    def patch(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        payload = request.data or {}
        updated = False
        for field in ('pin_login', 'face_id'):
            if field in payload:
                setattr(settings_obj, field, bool(payload.get(field)))
                updated = True
        if updated:
            settings_obj.save(update_fields=['pin_login', 'face_id', 'updated_at'])
        return Response({
            'status': 'ok',
            'settings': {
                'pin_login': settings_obj.pin_login,
                'face_id': settings_obj.face_id
            }
        })
