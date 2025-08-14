import logging
import os
from email.mime.image import MIMEImage
from typing import Dict, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import get_template

from premailer import transform
from solo.models import SingletonModel

logger = logging.getLogger(__name__)


def build_email_messages(
    template_path_txt: str, template_path_html: str, context: Dict
):
    email_txt_template = get_template(template_path_txt)
    email_html_template = get_template(template_path_html)

    email_message = email_txt_template.render(context)
    email_html_message = email_html_template.render(context)
    inlined_email_html_message = transform(email_html_message)
    return email_message, inlined_email_html_message


def create_email(
    subject: str,
    body: str,
    inlined_body: str,
    to: str,
    from_email: str = "",
    bcc: Optional[list[str]] = None,
    reply_to: Optional[list[str]] = None,
    config: Optional[SingletonModel] = None,
    connection: Optional[EmailBackend] = None,
    attachments: Optional[
        list[tuple[str, bytes, str]]
    ] = None,  # List of (filename, content, mimetype)
):
    """
    Create an email message with optional attachments.

    :param subject: Email subject
    :param body: Plain text email body
    :param inlined_body: HTML email body
    :param to: Recipient email address
    :param from_email: Sender email address
    :param bcc: List of BCC email addresses
    :param reply_to: List of reply-to email addresses
    :param attachments: List of attachments as tuples (filename, content, mimetype)
    """
    default_reply_to = (
        (getattr(config, "reply_to", None) or settings.KCC_DEFAULT_FROM_EMAIL)
        if not reply_to
        else reply_to
    )
    default_from_email = (
        (getattr(config, "from_email", None) or settings.KCC_DEFAULT_FROM_EMAIL)
        if not from_email
        else from_email
    )

    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=default_from_email,
        reply_to=default_reply_to or [],
        to=to,
        bcc=bcc or [],
        connection=connection if connection else None,
    )
    # Attach the plain text version
    email.attach_alternative(inlined_body, "text/html")

    # Attach the image
    filepath = os.path.join(settings.STATIC_ROOT, "img/wapen-utrecht-rood.svg")
    with open(filepath, "rb") as wapen:
        mime_image = MIMEImage(wapen.read())
        mime_image.add_header("Content-ID", "<wapen_utrecht_cid>")
        mime_image.add_header(
            "Content-Disposition", "inline", filename="wapen-utrecht-rood.svg"
        )
        email.attach(mime_image)

    if attachments:
        for filename, content, mimetype in attachments:
            email.attach(filename, content, mimetype)

    return email
