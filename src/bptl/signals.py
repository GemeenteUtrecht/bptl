from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Site)
def clear_logo_url_caching(sender, instance, created, **kwargs):
    cache.delete("utrecht_logo_url")
