from django.core.validators import EmailValidator
from django.template.loader import get_template

from premailer import transform
from rest_framework.exceptions import ValidationError

from bptl.openklant.client import get_openklant_client
from bptl.openklant.exceptions import EmailSendFailedException, OpenKlantEmailException
from bptl.openklant.models import OpenKlantConfig
from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .utils import build_email_context, create_email, get_actor_email_from_interne_taak


@register
class NotificeerBetrokkene(WorkUnit):
    """
    This task sends an email to ``receiver`` signed by ``sender``.
    """

    def perform(self):
        email_context = build_email_context(self.task)

        # Render email content
        email_openklant_message, inlined_email_html_message = (
            self._render_email_content(email_context)
        )

        # Get and validate email address
        emailaddress = self._get_and_validate_email_address()

        config = OpenKlantConfig.get_solo()
        send_to = []
        if config.debug:
            debug_email = config.debug_email
            send_to += [debug_email]

        # Create and send email
        send_to += [emailaddress]
        email = create_email(
            subject=email_context["subject"],
            body=email_openklant_message,
            inlined_body=inlined_email_html_message,
            to=send_to,
        )
        self._send_email(email)

    def _render_email_content(self, email_context):
        """
        Render the email content (plain text and HTML) and inline styles.
        """
        email_openklant_template = get_template("mails/openklant.txt")
        email_html_template = get_template("mails/openklant.html")

        email_openklant_message = email_openklant_template.render(email_context)
        email_html_message = email_html_template.render(email_context)
        inlined_email_html_message = transform(email_html_message)

        return email_openklant_message, inlined_email_html_message

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
