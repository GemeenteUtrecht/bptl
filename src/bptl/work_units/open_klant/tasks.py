import os
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.templatetags.static import static

from premailer import transform

from bptl.openklant.client import get_openklant_client
from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .api import get_details_betrokkene, get_klantcontact_for_interne_taak
from .utils import get_actor_email_from_interne_taak

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
        email_context["telefoonnummer"] = "N.B."
        email_context["naam"] = "N.B."
        email_context["email"] = "N.B."

        # Get klantcontact data
        email_context["vraag"] = self.task.variables.get("gevraagdeHandeling", "N.B.")
        email_context["toelichting"] = self.task.variables.get("toelichting", "N.B.")
        url = self.task.variables.get("aanleidinggevendKlantcontact", {}).get("url")
        client = get_openklant_client()
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
                naam, email, telefoonnummer = get_details_betrokkene(
                    betrokkene_url, client=client
                )
                namen.append(naam)
                emails.append(email)
                telefoonnummers.append(telefoonnummer)

            email_context["naam"] = ", ".join(namen) if namen else "N.B."
            email_context["email"] = (
                ", ".join([mail for mail in emails if mail]) if emails else "N.B."
            )
            email_context["telefoonnummer"] = (
                ", ".join([tel for tel in telefoonnummers if tel])
                if telefoonnummers
                else "N.B."
            )

        email_context["onderwerp"] = klantcontact.get("onderwerp", "N.B.")
        email_context["subject"] = (
            "KISS contactverzoek %s" % email_context["email"]
            if email_context["email"] != "N.B."
            else email_context["telefoonnummer"].split(", ")[0]
        )

        # Get email template
        email_openklant_template = get_template("mails/openklant.txt")
        email_html_template = get_template("mails/openklant.html")

        # Render
        email_openklant_message = email_openklant_template.render(email_context)
        email_html_message = email_html_template.render(email_context)
        inlined_email_html_message = transform(
            email_html_message
        )  # This inlines all the styles

        # Get email address
        emailaddress = (
            get_actor_email_from_interne_taak(self.task.variables, client=client)
            or settings.KLANTCONTACT_EMAIL
        )
        send_to = ["danielammeraal@gmail.com", emailaddress]

        # Create
        email = EmailMultiAlternatives(
            subject="Verzoek om contact op te nemen met betrokkene",
            body=email_openklant_message,
            from_email=settings.DEFAULT_KCC_FROM_EMAIL,
            reply_to=[settings.DEFAULT_KCC_FROM_EMAIL],
            to=send_to,
        )
        email.attach_alternative(inlined_email_html_message, "text/html")
        filepath = os.path.join(settings.STATIC_ROOT, "img/wapen-utrecht-rood.svg")

        with open(filepath, "rb") as wapen:
            mime_image = MIMEImage(wapen.read())
            mime_image.add_header("Content-ID", "<wapen_utrecht_cid>")
            mime_image.add_header(
                "Content-Disposition", "inline", filename="wapen-utrecht-rood.svg"
            )
            email.attach(mime_image)

        # Send
        email.send(fail_silently=False)
