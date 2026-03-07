from decimal import Decimal

from django.db import models
from django.db.models import F, Sum
from django.utils import timezone

from apps.products.models import Product
from apps.users.models import User


class Defect(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name="defects",
        verbose_name="Продукт",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defects",
        verbose_name="Сотрудник",
    )
    employee_task = models.ForeignKey(
        "employee_tasks.EmployeeTask",
        on_delete=models.SET_NULL,
        related_name="defects",
        null=True,
        blank=True,
        verbose_name="Задание сотрудника",
    )
    quantity = models.DecimalField(
        "Количество (кг)",
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
    )
    employee_comment = models.TextField("Комментарий сотрудника", blank=True)
    admin_comment = models.TextField("Комментарий администратора", blank=True)
    penalty_amount = models.DecimalField(
        "Сумма штрафа",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    penalty_assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_defect_penalties",
        verbose_name="Штраф назначил",
    )
    penalty_assigned_at = models.DateTimeField(
        "Дата назначения штрафа",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    def __str__(self):
        product_name = self.product.name if self.product else "Без продукта"
        employee_name = self.user.get_full_name() if self.user else "Без сотрудника"
        return f"Брак: {product_name} - {employee_name}"

    def apply_penalty(self, amount, assigned_by=None, admin_comment=None):
        if amount is None and admin_comment is None:
            return

        previous_amount = Decimal(str(self.penalty_amount or 0))
        new_amount = Decimal(str(amount)) if amount is not None else Decimal("0")
        delta = new_amount - previous_amount

        if amount is None:
            self.penalty_amount = None
        else:
            self.penalty_amount = new_amount

        if admin_comment is not None:
            self.admin_comment = admin_comment
        if assigned_by is not None:
            self.penalty_assigned_by = assigned_by
        self.penalty_assigned_at = timezone.now()
        self.save()

        if self.user and delta != 0:
            User.objects.filter(pk=self.user_id).update(balance=F("balance") - delta)

    @property
    def reworked_quantity(self):
        """
        Общее количество брака, уже переработанное в сырьё.
        """
        total = self.reworks.aggregate(total=Sum("input_quantity")).get("total") or Decimal(
            "0"
        )
        return Decimal(str(total))

    @property
    def available_for_rework(self):
        """
        Сколько брака ещё доступно для переработки.
        """
        base = Decimal(str(self.quantity or 0))
        return max(base - self.reworked_quantity, Decimal("0"))

    class Meta:
        verbose_name = "Брак"
        verbose_name_plural = "Браки"
        ordering = ["-created_at"]


class DefectRework(models.Model):
    """
    Переработка брака сотрудником «обрабатывающего» цеха (ID4).

    Логируем, сколько брака взяли и в какое сырьё его превратили.
    """

    defect = models.ForeignKey(
        Defect,
        on_delete=models.CASCADE,
        related_name="reworks",
        verbose_name="Брак",
    )
    raw_material = models.ForeignKey(
        "factory_inventory.RawMaterial",
        on_delete=models.PROTECT,
        related_name="defect_reworks",
        verbose_name="Сырьё после переработки",
    )
    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defect_reworks",
        verbose_name="Сотрудник переработки",
    )
    workshop = models.ForeignKey(
        "operations_workshops.Workshop",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defect_reworks",
        verbose_name="Цех переработки",
    )
    input_quantity = models.DecimalField(
        "Кол-во брака (кг)",
        max_digits=12,
        decimal_places=3,
    )
    output_quantity = models.DecimalField(
        "Кол-во сырья (кг)",
        max_digits=12,
        decimal_places=3,
    )
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Переработка брака"
        verbose_name_plural = "Переработки брака"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Переработка брака #{self.defect_id} → "
            f"{self.raw_material.name} ({self.output_quantity} кг)"
        )
