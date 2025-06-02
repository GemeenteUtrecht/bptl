"""Celery tasks to process OpenKlant internal tasks."""

import csv
from datetime import datetime
from io import StringIO

from django.conf import settings
from django.template.loader import get_template

from celery.utils.log import get_task_logger
from celery_once import QueueOnce
from premailer import transform
from timeline_logger.models import TimelineLog

from bptl.openklant.models import FailedOpenKlantTasks
from bptl.tasks.api import execute
from bptl.tasks.registry import register
from bptl.utils.constants import Statuses
from bptl.utils.decorators import retry
from bptl.work_units.open_klant.utils import (
    build_email_context,
    create_email,
    get_actor_email_from_interne_taak,
)

from ..celery import app
from .client import get_openklant_client
from .constants import FailedTaskStatuses
from .models import OpenKlantConfig, OpenKlantInternalTaskModel
from .utils import fetch_and_patch, save_failed_task

logger = get_task_logger(__name__)


@app.task(
    base=QueueOnce,
    autoretry_for=(Exception,),
    retry_backoff=True,
    once={"graceful": True, "timeout": 60},
)
def task_fetch_and_patch():
    """Fetch and lock tasks for processing."""
    logger.debug("Fetching and locking tasks (long poll)")
    worker_id, num_tasks, tasks = fetch_and_patch()
    logger.info("Fetched %r tasks with %r", num_tasks, worker_id)

    for task in tasks:
        TimelineLog.objects.create(
            content_object=task, extra_data={"status": task.status}
        )
        task_execute.delay(task.id)

    task_schedule_new_fetch_and_patch.apply_async(countdown=60)
    return num_tasks


@app.task()
def task_schedule_new_fetch_and_patch():
    """Schedule a new fetch and patch task."""
    task_fetch_and_patch.apply_async(countdown=60)


@retry(
    times=5,
    delay=3.0,
    exponential_rate=2.0,
    exceptions=(Exception,),
    on_failure=lambda exc, task: save_failed_task(task, exc),
)
def _execute(fetched_task: OpenKlantInternalTaskModel):
    """Execute a fetched task."""
    execute(fetched_task, registry=register)


@app.task()
def task_execute(fetched_task_id):
    """Execute a specific task by its ID."""
    logger.info("Received task execution request (ID %d)", fetched_task_id)
    fetched_task = OpenKlantInternalTaskModel.objects.get(id=fetched_task_id)

    if fetched_task.status != Statuses.initial:
        logger.warning("Task %r has already been run", fetched_task_id)
        return

    logger.info("Task UUID is %s", fetched_task.task_id)
    fetched_task.status = Statuses.in_progress
    fetched_task.save(update_fields=["status"])

    try:
        _execute(fetched_task)
    except Exception as exc:
        logger.warning(
            "Task %r failed during execution with error: %r",
            fetched_task_id,
            exc,
            exc_info=True,
        )
        return

    logger.info("Task %r executed successfully", fetched_task_id)


@app.task(
    base=QueueOnce,
    once={"graceful": True, "timeout": settings.CELERY_QUEUE_ONCE_TIMEOUT},
)
def retry_failed_tasks():
    """Retry tasks that previously failed."""
    logger.info("Started retrying failed tasks.")
    failed_tasks = FailedOpenKlantTasks.objects.filter(
        status=FailedTaskStatuses.initial
    )
    failed_again = []
    client = get_openklant_client()

    for failed_task in failed_tasks:
        task = failed_task.task
        try:
            _execute(task)
            update_task_status(failed_task, client, task, success=True)
        except Exception as e:
            logger.warning(
                "Retry failed for task %r: %r", failed_task.task.id, e, exc_info=True
            )
            update_task_status(failed_task, client, task, success=False)
            failed_again.append(failed_task)

    notify_failed_tasks(failed_again, client)


def update_task_status(failed_task, client, task, success):
    """Update the status of a task in OpenKlant."""
    failed_task.status = (
        FailedTaskStatuses.succeeded if success else FailedTaskStatuses.failed
    )
    failed_task.save(update_fields=["status"])

    if success:
        tijd = datetime.now().isoformat()
        toelichting = "[BPTL] - {tijd}: Succesvol afgerond. \n\n {toelichting}".format(
            tijd=tijd, toelichting=task.variables.get("toelichting", "")
        )
        client.partial_update(
            "internetaak",
            {"toelichting": toelichting},
            url=task.variables["url"],
        )


def notify_failed_tasks(failed_again, client):
    """Notify about tasks that failed again."""
    if not failed_again:
        logger.info("No failed tasks to notify.")
        return

    logger.info("%d tasks failed again. Notifying the receiver.", len(failed_again))
    failed_data = collect_failed_task_data(failed_again, client)
    send_failure_notification(failed_data)


def collect_failed_task_data(failed_again, client):
    """Collect data for failed tasks."""
    failed_data = []

    for failed_task in failed_again:
        task = failed_task.task
        email_context = build_email_context(task, client=client)
        try:
            medewerker_email = get_actor_email_from_interne_taak(
                task.variables, client=client
            )
        except Exception:
            medewerker_email = "N.B. <- ?ERROR?"

        failed_data.append(
            {
                "email": email_context["email"],
                "klantcontact_nummer": email_context["klantcontact"].get(
                    "nummer", "N.B."
                ),
                "klantcontact_uuid": email_context["klantcontact"].get("uuid", "N.B."),
                "klantcontact_naam": email_context["naam"],
                "klantcontact_onderwerp": email_context["onderwerp"],
                "klantcontact_telefoonnummer": email_context["telefoonnummer"],
                "klantcontact_toelichting": email_context["toelichting"],
                "klantcontact_vraag": email_context["vraag"],
                "medewerker_email": medewerker_email,
                "reden_error": failed_task.reason,
            }
        )

    return failed_data


def send_failure_notification(failed_data):
    """Send an email notification about failed tasks."""
    email_openklant_template = get_template("mails/openklant_failed.txt")
    email_html_template = get_template("mails/openklant_failed.html")

    email_openklant_message = email_openklant_template.render(
        {"aantal": len(failed_data)}
    )
    email_html_message = email_html_template.render({"aantal": len(failed_data)})
    inlined_email_html_message = transform(email_html_message)

    config = OpenKlantConfig.get_solo()
    send_to = [config.logging_email]
    csv_content = generate_csv_content(failed_data)

    attachments = [("failed_tasks.csv", csv_content.encode("utf-8"), "text/csv")]
    email = create_email(
        subject="Logging gefaalde KCC contactverzoeken",
        body=email_openklant_message,
        inlined_body=inlined_email_html_message,
        to=send_to,
        attachments=attachments,
    )
    email.send(fail_silently=False)


def generate_csv_content(failed_data):
    """Generate CSV content for failed tasks."""
    with StringIO() as csv_buffer:
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(
            [
                "Email",
                "Klantcontact Nummer",
                "Klantcontact UUID",
                "Klantcontact Naam",
                "Klantcontact Onderwerp",
                "Klantcontact Telefoonnummer",
                "Klantcontact Toelichting",
                "Klantcontact Vraag",
                "Groep/Medewerker Email",
                "Reden Error",
            ]
        )
        for task in failed_data:
            csv_writer.writerow(
                [
                    task["email"],
                    task["klantcontact_nummer"],
                    task["klantcontact_uuid"],
                    task["klantcontact_naam"],
                    task["klantcontact_onderwerp"],
                    task["klantcontact_telefoonnummer"],
                    task["klantcontact_toelichting"],
                    task["klantcontact_vraag"],
                    task["medewerker_email"],
                    task["reden_error"],
                ]
            )
        return csv_buffer.getvalue()
