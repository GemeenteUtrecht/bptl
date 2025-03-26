from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.templatetags.static import static

from bptl.openklant.client import get_openklant_client
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

        # Get logo url
        site = Site.objects.get_current()
        protocol = "https" if settings.IS_HTTPS else "http"
        logo_url = f"{protocol}://{site.domain}{static('img/wapen-utrecht-rood.svg')}"

        # Set email context
        email_context = {"logo_url": logo_url}
        email_context["telefoonnummer"] = "N.B."
        email_context["naam"] = "N.B."
        email_context["email"] = "N.B."

        # Get klantcontact data
        email_context["vraag"] = self.task.variables.get("gevraagdeHandeling", "N.B.")
        email_context["toelichting"] = self.task.variables.get("toelichting", "N.B.")
        client = get_openklant_client()
        url = self.task.variables.get("aanleidinggevendKlantcontact", {}).get("url")
        if url:
            klantcontact = client.retrieve(
                "klantcontact", url=url, query_params={"expand": "hadBetrokkenen"}
            )
            betrokkenen = [
                betrokkene
                for betrokkene in klantcontact.get("hadBetrokkenen", [])
                if betrokkene
            ]
            telefoonnummers = []
            namen = []
            emails = []
            for betr in betrokkenen:
                telefoonnummers.append(betr.get("telefoonnummer", "N.B.,"))
                namen.append(betr.get("volledigeNaam", "N.B."))
                emails.append(betr.get("email", "N.B"))
            email_context["telefoonnummer"] = ", ".join(telefoonnummers)
            email_context["naam"] = ", ".join(namen)
            email_context["email"] = ", ".join(emails)

        # Get email template
        email_openklant_template = get_template("email/mails/openklant.txt")
        email_html_template = get_template("email/mails/openklant.html")

        # Render
        email_openklant_message = email_openklant_template.render(email_context)
        email_html_message = email_html_template.render(email_context)

        # Create
        email = EmailMultiAlternatives(
            subject="Verzoek om contact op te nemen met betrokkene",
            body=email_openklant_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            reply_to=[settings.DEFAULT_FROM_EMAIL],
            to=["danielammeraal@gmail.com"],
        )
        email.attach_alternative(email_html_message, "text/html")

        # Send
        email.send(fail_silently=False)
