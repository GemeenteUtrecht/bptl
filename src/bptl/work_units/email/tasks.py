from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.api_models.base import factory

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .serializers import SendEmailSerializer, ValidTemplateChoices

__all__ = ["SendEmail"]


@register
class SendEmailTask(WorkUnit):
    """This task sends an email to ``receiver`` signed by ``sender``.

    **Required process variables**

    * ``sender``: JSON with email and name of sender.
        .. code-block:: json
                {
                    "email": "kees@example.com",
                    "name": "Kees Koos"
                }

    * ``receiver``: JSON with email and name of receiver.
        .. code-block:: json
                {
                    "email": "jan@example.com",
                    "name": "Jan Janssen"
                }

    * ``email``: JSON with email variables:
        .. code-block:: json
                {
                    "subject": "This is an example subject.",
                    "content": "This is an example body."
                }

    * ``template``: string with template name. Choices:
        .. code-block:: list
                [
                    generiek, accordering, advies,
                ]

    **Optional process variables**

    * ``kownslFrontendUrl``: string with full URL for end users to submit their review.
                Valid choices are currently: generic/approval/advice.
    * ``reminder``: boolean.
    * ``deadline``: datetime: "2020-04-20 16:20:00".
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
            **send_email["kwargs"],
        }

        # Get email template
        template_path = ValidTemplateChoices.labels[send_email["template"]]
        email_template = get_template(template_path)

        # If email is a reminder, add reminder to subject line
        if send_email["kwargs"]["reminder"]:
            send_email["email"][
                "subject"
            ] = f"HERINNERING: {send_email['email']['subject']}"

        # Render and send
        email_message = email_template.render(email_context)
        send_mail(
            subject=send_email["email"]["subject"],
            message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[send_email["receiver"]["email"]],
        )
