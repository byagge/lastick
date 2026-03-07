from django.shortcuts import redirect
from django.conf import settings
from apps.users.models import User


class BlockedUserMiddleware:
    """
    Middleware для мгновенного редиректа заблокированных пользователей
    на страницу /banned при попытке открыть любую страницу сайта.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = request.path

        # Разрешенные пути для заблокированных пользователей
        allowed_paths = {
            "/banned/",
            settings.LOGIN_URL,
        }
        # Также пропускаем статику и медиа
        is_static = path.startswith(settings.STATIC_URL) if getattr(settings, "STATIC_URL", None) else False
        is_media = path.startswith(settings.MEDIA_URL) if getattr(settings, "MEDIA_URL", None) else False

        if (
            user
            and user.is_authenticated
            and getattr(user, "is_blocked", False)
            and path not in allowed_paths
            and not is_static
            and not is_media
        ):
            return redirect("/banned/")

        response = self.get_response(request)
        return response


class RoleBasedRedirectMiddleware:
    """
    Middleware для редиректа пользователей на соответствующие страницы
    на основе их ролей при посещении корневого URL (/)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем, является ли это запрос к корневому URL
        if request.path == '/' and request.user.is_authenticated:
            # Получаем роль пользователя
            user_role = getattr(request.user, 'role', None)
            
            # Определяем URL для редиректа на основе роли
            redirect_url = self.get_redirect_url_by_role(user_role)
            
            if redirect_url and redirect_url != request.path:
                return redirect(redirect_url)
        
        response = self.get_response(request)
        return response

    def get_redirect_url_by_role(self, role):
        """
        Возвращает URL для редиректа на основе роли пользователя
        """
        if not role:
            return None
            
        role_redirects = {
            User.Role.ADMIN: '/dashboard/',  # Администратор -> дашборд
            User.Role.ACCOUNTANT: '/finance/',  # Бухгалтер -> финансы
            User.Role.WORKER: '/employee_tasks/tasks/',  # Рабочий -> задачи сотрудника
        }
        
        return role_redirects.get(role, None)


class AuthenticationErrorMiddleware:
    """
    Middleware для обработки ошибок аутентификации и авторизации
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Если получили 401 статус, перенаправляем на страницу ошибки
        if response.status_code == 401:
            from .error_views import custom_401
            return custom_401(request)
        
        return response 