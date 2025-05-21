from django.core.validators import EmailValidator
from django.template.loader import get_template

from premailer import transform

from bptl.openklant.client import get_openklant_client
from bptl.openklant.exceptions import OpenKlantEmailException
from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .utils import build_email_context, create_email, get_actor_email_from_interne_taak

__all__ = ["SendEmailTask"]


@register
class NotificeerBetrokkene(WorkUnit):
    """
    This task sends an email to ``receiver`` signed by ``sender``.
    """

    def perform(self):
        email_context = build_email_context(self.task)

        # Get email template
        email_openklant_template = get_template("mails/openklant.txt")
        email_html_template = get_template("mails/openklant.html")

        # Render
        email_openklant_message = email_openklant_template.render(email_context)
        email_html_message = email_html_template.render(email_context)
        # This inlines all the styles
        inlined_email_html_message = transform(email_html_message)

        # Get email address
        client = get_openklant_client()
        emailaddress = get_actor_email_from_interne_taak(
            self.task.variables, client=client
        )

        # Validate email address
        email_validator = EmailValidator()
        try:
            email_validator(emailaddress)
        except ValidationError as e:
            self.task.status = "failed"
            self.task.save(update_fields=["status"])
            raise OpenKlantEmailException(
                f"Invalid email address: {emailaddress}. Error: {e}"
            )

        send_to = ["danielammeraal@gmail.com", emailaddress]
        email = create_email(
            subject=email_context["subject"],
            body=email_openklant_message,
            inlined_body=inlined_email_html_message,
            to=send_to,
        )

        # Send
        success = email.send(fail_silently=False)
        if not success:
            self.task.status = "failed"
            self.task.save(update_fields=["status"])
            raise OpenKlantEmailException("Failed to send email.")
        else:
            self.task.status = "success"
            self.task.save(update_fields=["status"])
