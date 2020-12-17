from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import get_template

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .serializers import VALID_TEMPLATE_CHOICES, SendEmailSerializer

__all__ = ["SendEmailTask"]


@register
class SendEmailTask(WorkUnit):
    """This task sends an email to ``receiver`` signed by ``sender``.

    **Required process variables**

    * ``sender``: JSON with required fields email and name of sender.

        .. code-block:: json

            {
              "email": "kees@example.com",
              "name": "Kees Koos"
            }

    * ``receiver``: JSON with required fields email and name of receiver.

        .. code-block:: json

            {
              "email": "jan@example.com",
              "name": "Jan Janssen"
            }

    * ``email``: JSON with required fields email subject and email content:

        .. code-block:: json

            {
              "subject": "This is an example subject.",
              "content": "This is an example body."
            }

    * ``template``: string with template name. Valid choices are:

        .. code-block:: json

            [
              "generiek",
              "accordering",
              "advies",
              "nen2580"
            ]

    * ``context``: JSON with optional fields:

        .. code-block:: json

            {
              "kownslFrontendUrl": "https://kownsl.utrechtproeftuin.nl/kownsl/<uuid>/",
              "reminder": True,
              "deadline`": "2020-04-20"
            }
    """

    def perform(self):
        variables = self.task.get_variables()
        send_email = SendEmailSerializer(data=variables)
        send_email.is_valid(raise_exception=True)
        send_email = send_email.validated_data

        # Set email context
        email_context = {
            "sender": send_email["sender"],
            "receiver": send_email["receiver"],
            "email": send_email["email"],
            "review_type": send_email["template"],
            **send_email["context"],
        }

        # Get email template
        template_path = VALID_TEMPLATE_CHOICES[send_email["template"]]
        email_template = get_template(template_path)

        # If email is a reminder, add reminder to subject line
        if send_email["context"].get("reminder", ""):
            send_email["email"][
                "subject"
            ] = f"HERINNERING: {send_email['email']['subject']}"

        # Render and send
        email_message = email_template.render(email_context)
        email = EmailMessage(
            subject=send_email["email"]["subject"],
            body=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            reply_to=[send_email["sender"]["email"]],
            to=[send_email["receiver"]["email"]],
        )
        email.send(fail_silently=False)
