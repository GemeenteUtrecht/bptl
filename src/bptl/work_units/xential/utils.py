import binascii
import logging
from base64 import b64decode
from urllib.parse import urlparse

from django.utils.translation import gettext_lazy as _

from defusedxml import minidom
from drf_extra_fields.fields import Base64FileField
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


def parse_xml(raw_xml: str) -> dict:
    parsed_xml = minidom.parseString(raw_xml)  # minidom from defusedxml
    extracted_data = {}

    document_node = parsed_xml.getElementsByTagName("document")
    extracted_data["document"] = document_node[0].firstChild.nodeValue

    ticket_node = parsed_xml.getElementsByTagName("bptlTicketUuid")
    extracted_data["bptl_ticket_uuid"] = ticket_node[0].firstChild.nodeValue

    return extracted_data


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
