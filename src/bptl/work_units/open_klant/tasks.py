from django.conf import settings
from django.core.validators import EmailValidator

from rest_framework.exceptions import ValidationError

from bptl.openklant.client import get_openklant_client
from bptl.openklant.exceptions import EmailSendFailedException, OpenKlantEmailException
from bptl.openklant.mail_backend import KCCEmailConfig
from bptl.openklant.models import OpenKlantConfig
from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register
from bptl.work_units.mail.mail import build_email_messages, create_email
from bptl.work_units.open_klant.mail import get_kcc_email_connection

from .utils import build_email_context, get_actor_email_from_interne_taak


@register
class NotificeerBetrokkene(WorkUnit):
    """
    This task sends an email to ``receiver`` signed by ``sender``.
    """

    def perform(self):
        email_context = build_email_context(self.task)

        # Render email content
        email_openklant_message, inlined_email_html_message = build_email_messages(
            "mails/openklant.txt", "mails/openklant.html", email_context
        )

        # Get and validate email address
        emailaddress = self._get_and_validate_email_address()

        config = OpenKlantConfig.get_solo()
        bcc = [config.debug_email] if config.debug_email else []

        # Create and send email
        send_to = [emailaddress]
        email_config = KCCEmailConfig.get_solo()
        connection = get_kcc_email_connection()
        email = create_email(
            subject=email_context["subject"],
            body=email_openklant_message,
            inlined_body=inlined_email_html_message,
            to=send_to,
            from_email=email_config.from_email or settings.KCC_DEFAULT_FROM_EMAIL,
            bcc=bcc,
            reply_to=email_config.reply_to or settings.KCC_DEFAULT_FROM_EMAIL,
            config=email_config,
            connection=connection,
        )
        self._send_email(email)

    def _get_and_validate_email_address(self):
        """
        Retrieve and validate the email address of the actor.
        """
        client = get_openklant_client()
        emailaddress = get_actor_email_from_interne_taak(
            self.task.variables, client=client
        )

        email_validator = EmailValidator()
        try:
            email_validator(emailaddress)
        except ValidationError as e:
            self._mark_task_as_failed()
            raise OpenKlantEmailException(
                f"Invalid email address: {emailaddress}. Error: {e}"
            )

        return emailaddress

    def _send_email(self, email):
        """
        Send the email and handle success or failure.
        """
        success = email.send(fail_silently=False)
        if not success:
            self._mark_task_as_failed()
            raise EmailSendFailedException()
        else:
            self._mark_task_as_success()

    def _mark_task_as_failed(self):
        """
        Mark the task as failed and save the status.
        """
        self.task.status = "failed"
        self.task.save(update_fields=["status"])

    def _mark_task_as_success(self):
        """
        Mark the task as successful and save the status.
        """
        self.task.status = "success"
        self.task.save(update_fields=["status"])
