from django.contrib import admin

from .models import Defect


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "product",
        "user",
        "quantity",
        "penalty_amount",
        "penalty_assigned_by",
        "created_at",
    ]
    list_filter = ["created_at", "penalty_assigned_by", "user__workshop"]
    search_fields = [
        "product__name",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = ["created_at", "penalty_assigned_at"]
    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "product",
                    "user",
                    "employee_task",
                    "quantity",
                    "employee_comment",
                )
            },
        ),
        (
            "Штраф",
            {
                "fields": (
                    "penalty_amount",
                    "admin_comment",
                    "penalty_assigned_by",
                    "penalty_assigned_at",
                )
            },
        ),
        ("Служебное", {"fields": ("created_at",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "product",
            "user",
            "penalty_assigned_by",
            "employee_task",
        )
