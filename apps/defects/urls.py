from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"defects", views.DefectViewSet)

urlpatterns = [
    path("", views.defects_page, name="defects_page"),
    path("mobile/", views.defects_mobile_page, name="defects_mobile_page"),
    path("api/", include(router.urls)),
    path(
        "api/defects/<int:defect_id>/assign_penalty/",
        views.assign_penalty,
        name="assign_penalty",
    ),
    path("api/stats/", views.defects_stats, name="defects_stats"),
]
