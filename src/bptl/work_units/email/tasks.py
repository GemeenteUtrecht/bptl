from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .serializers import VALID_TEMPLATE_CHOICES, SendEmailSerializer

__all__ = ["SendEmailTask"]


@register
class SendEmailTask(WorkUnit):
    """This task sends an email to ``receiver`` signed by ``sender``.

    **Required process variables**

    * ``sender`` [json]: required fields email and name of sender.

        .. code-block:: json

            {
              "email": "voornaam.achternaam@example.com",
              "name": "Voornaam Achternaam"
            }

    * ``receiver`` [json]: required fields email and name of receiver.

        .. code-block:: json

            {
              "email": "voornaam.achternaam@example.com",
              "name": "Voornaam Achternaam"
            }

    * ``email`` [json]: required fields email subject and email content:

        .. code-block:: json

            {
              "subject": "This is an example subject.",
              "content": "This is an example body."
            }

    * ``template`` [str]: template name. Valid choices are:

        .. code-block:: json

            [
              "generiek",
              "accordering",
              "advies",
              "nen2580",
              "verzoek_afgehandeld"
            ]

    * ``context`` [json]: JSON with fields depending on the template:

        .. code-block:: json

            {
              "reviewType": "accordering/advies",
              "doReviewUrl": "https://kownsl.cg-intern.*.utrecht.nl/kownsl/<uuid>/",
              "deadline`": "2020-04-20"
            }

    """

    def perform(self):
        variables = self.task.get_variables()
        send_email = SendEmailSerializer(data=variables)
        send_email.is_valid(raise_exception=True)

        # Set email context
        email_context = {
            "sender": send_email.data["sender"],
            "receiver": send_email.data["receiver"],
            "email": send_email.data["email"],
            "subject": send_email.data["email"]["subject"],
            **send_email.data["context"],
        }

        # Get email template
        template_path = VALID_TEMPLATE_CHOICES[send_email.data["template"]]
        email_plain_template = get_template(template_path["plain"])
        email_html_template = get_template(template_path["html"])

        # Render
        email_plain_message = email_plain_template.render(email_context)
        email_html_message = email_html_template.render(email_context)

        # Create
        email = EmailMultiAlternatives(
            subject=send_email.data["email"]["subject"],
            body=email_plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            reply_to=[send_email.data["sender"]["email"]],
            to=[send_email.data["receiver"]["email"]],
        )
        email.attach_alternative(email_html_message, "text/html")

        # Send
        email.send(fail_silently=False)
