from celery import Celery

from camunda_worker.setup import setup_env

setup_env()

app = Celery("camunda_worker")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
