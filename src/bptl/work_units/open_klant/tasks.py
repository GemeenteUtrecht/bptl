from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.templatetags.static import static

from bptl.openklant.client import get_openklant_client
from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .api import get_details_betrokkene, get_klantcontact_for_interne_taak
from .utils import get_actor_email_from_interne_taak, get_logo_url

__all__ = ["SendEmailTask"]


@register
class NotificeerBetrokkene(WorkUnit):
    """
    This task sends an email to ``receiver`` signed by ``sender``.
    """

    def perform(self):
        variables = self.task.variables

        logo_url = get_logo_url()
        # Set email context
        email_context = {"logo_url": logo_url}
        email_context["telefoonnummer"] = "N.B."
        email_context["naam"] = "N.B."
        email_context["email"] = "N.B."

        # Get klantcontact data
        email_context["vraag"] = self.task.variables.get("gevraagdeHandeling", "N.B.")
        email_context["toelichting"] = self.task.variables.get("toelichting", "N.B.")
        url = self.task.variables.get("aanleidinggevendKlantcontact", {}).get("url")
        if url:
            klantcontact = get_klantcontact_for_interne_taak(url)
            betrokkenen = [
                betrokkene["url"]
                for betrokkene in klantcontact.get("hadBetrokkenen", [])
                if betrokkene.get("url")
            ]
            namen = []
            emails = []
            telefoonnummers = []
            for betrokkene_url in betrokkenen:
                naam, email, telefoonnummer = get_details_betrokkene(betrokkene_url)
                namen.append(naam)
                emails.append(email)
                telefoonnummers.append(telefoonnummer)

            email_context["naam"] = ", ".join(namen) if namen else "N.B."
            email_context["email"] = ", ".join(emails) if emails else "N.B."
            email_context["telefoonnummer"] = (
                ", ".join(telefoonnummers) if telefoonnummers else "N.B."
            )

        email_context["onderwerp"] = klantcontact.get("onderwerp", "N.B.")
        email_context["subject"] = (
            "Klantcontact: Verzoek om contact op te nemen met betrokkene"
        )

        # Get email template
        email_openklant_template = get_template("email/mails/openklant.txt")
        email_html_template = get_template("email/mails/openklant.html")

        # Render
        email_openklant_message = email_openklant_template.render(email_context)
        email_html_message = email_html_template.render(email_context)

        # Get email address
        emailaddress = (
            get_actor_email_from_interne_taak(self.task.variables)
            or settings.KLANTCONTACT_EMAIL
        )
        send_to = ["danielammeraal@gmail.com", emailaddress]

        # Create
        email = EmailMultiAlternatives(
            subject="Verzoek om contact op te nemen met betrokkene",
            body=email_openklant_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            reply_to=[settings.DEFAULT_FROM_EMAIL],
            to=send_to,
        )
        email.attach_alternative(email_html_message, "text/html")

        # Send
        email.send(fail_silently=False)
