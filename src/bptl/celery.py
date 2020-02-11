from celery import Celery

from bptl.setup import setup_env

setup_env()

app = Celery("bptl")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
