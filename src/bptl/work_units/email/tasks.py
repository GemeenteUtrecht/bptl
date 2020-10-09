from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import get_template

from zgw_consumers.api_models.base import factory

from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.registry import register

from .data import Email, EmailPerson

__all__ = ["SendEmail"]


@register
class SendEmailTask(WorkUnit):
    """This task sends an email to ``receiver`` signed by ``sender``.

    **Required process variables**

    * ``zaakUrl``: string. Full url of the zaak.
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
                        "body": "This is an example body."
                    }
    """

    def perform(self):
        variables = self.task.get_variables()
        sender = check_variable(variables, "sender")
        receiver = check_variable(variables, "receiver")
        email = check_variable(variables, "email")

        sender = factory(EmailPerson, sender)
        receiver = factory(EmailPerson, receiver)
        email = factory(Email, email)

        email_template = get_template("../templates/generic_email.txt")
        email_context = {
            "sender": sender,
            "receiver": receiver,
            "email": email,
        }

        email_message = email_template.render(email_context)
        send_mail(
            subject=email.subject,
            message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[receiver.email],
        )
