from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


ALLOWED_ROLES = { 'admin' }


def _has_director_access(user) -> bool:
	try:
		return bool(getattr(user, 'is_superuser', False)) or getattr(user, 'role', None) in ALLOWED_ROLES
	except Exception:
		return False


@login_required
def dashboard(request):
	if not _has_director_access(request.user):
		return redirect('/dashboard/')
	# Detect mobile device
	ua = (request.META.get('HTTP_USER_AGENT', '') or '').lower()
	is_mobile = any(m in ua for m in ['android', 'iphone', 'ipad', 'mobile'])
	template = 'director/dashboard_mobile.html' if is_mobile else 'director/dashboard.html'
	return render(request, template)


@login_required
def dashboard_mobile(request):
	if not _has_director_access(request.user):
		return redirect('/dashboard/')
	return render(request, 'director/dashboard_mobile.html')
