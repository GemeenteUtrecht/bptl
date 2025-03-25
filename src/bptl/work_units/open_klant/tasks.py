from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

__all__ = ["SendEmailTask"]


@register
class NotificeerBetrokkene(WorkUnit):
    """
    This task sends an email to ``receiver`` signed by ``sender``.
    """

    def perform(self):
        variables = self.task.variables

        # Set email context
        email_context = {}

        # Get email template
        #  template_path =
        email_openklant_template = get_template("email/mails/openklant.txt")
        # email_html_template = get_template(template_path["html"])

        # Render
        email_openklant_message = email_openklant_template.render(email_context)
        # email_html_message = email_html_template.render(email_context)

        # Create
        email = EmailMultiAlternatives(
            subject="test email",
            body=email_openklant_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            reply_to=settings.DEFAULT_FROM_EMAIL,
            to=["danielammeraal@gmail.com"],
        )
        # email.attach_alternative(email_html_message, "text/html")

        # Send
        email.send(fail_silently=False)
