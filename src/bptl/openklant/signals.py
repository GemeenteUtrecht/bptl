from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import InterneTask


@receiver(post_save, sender=InterneTask)
def clear_logo_url_caching(sender, instance, created, **kwargs):
    cache.delete("interne_task_gevraagde_handelingen")
