import binascii
import logging
from base64 import b64decode
from urllib.parse import urlparse

from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.util import underscoreize
from drf_extra_fields.fields import Base64FileField
from rest_framework.exceptions import ValidationError
from rest_framework_xml.parsers import XMLParser

from bptl.tasks.base import MissingVariable

logger = logging.getLogger(__name__)


def get_xential_base_url(api_root: str) -> str:
    parsed_url = urlparse(api_root)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


class AnyFileType:
    def __contains__(self, item):
        return True


class Base64Document(Base64FileField):
    ALLOWED_TYPES = AnyFileType()

    def get_file_extension(self, filename, decoded_file):
        return "bin"

    def to_internal_value(self, base64_data):
        try:
            # If validate is False, no check is done to see if the data contains non base-64 alphabet characters
            b64decode(base64_data, validate=True)
        except binascii.Error as e:
            if str(e) == "Incorrect padding":
                logger.warning("Document received from Xential has incorrect padding.")
                raise ValidationError(
                    _("The provided base64 data has incorrect padding"),
                    code="incorrect-base64-padding",
                )
            raise ValidationError(str(e), code="invalid-base64")
        except TypeError as exc:
            raise ValidationError(str(exc))

        return super().to_internal_value(base64_data)


def check_document_api_required_fields(document_properties: dict) -> None:
    required_fields = [
        "bronorganisatie",
        "titel",
        "auteur",
        "informatieobjecttype",
    ]

    missing_fields = []
    for field_name in required_fields:
        if field_name not in document_properties:
            missing_fields.append(field_name)

    if len(missing_fields) > 0:
        error_message = _(
            "The Documenten API expects the following properties to be provided: %(variables)s. "
            "Please add them to the documentMetadata process variable."
        ) % {"variables": ", ".join(missing_fields)}
        raise MissingVariable(error_message)


class SnakeXMLParser(XMLParser):
    def parse(self, stream, media_type=None, parser_context=None):
        camel_data = super().parse(stream, media_type, parser_context)
        return underscoreize(camel_data)
