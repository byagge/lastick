from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Workshop, WorkshopMaster


@receiver(pre_save, sender=Workshop)
def update_manager_role(*args, **kwargs):
    return


@receiver(post_save, sender=Workshop)
def ensure_manager_role(*args, **kwargs):
    return


@receiver(post_save, sender=WorkshopMaster)
def update_workshop_master_role(*args, **kwargs):
    return


@receiver(post_save, sender=WorkshopMaster)
def handle_workshop_master_status_change(*args, **kwargs):
    return


@receiver(post_delete, sender=WorkshopMaster)
def handle_workshop_master_deletion(*args, **kwargs):
    return

