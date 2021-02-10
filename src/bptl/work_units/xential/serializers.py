import binascii
from base64 import b64decode

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class CallbackDataSerializer(serializers.Serializer):
    bptl_ticket_uuid = serializers.UUIDField(label=_("BPTL ticket UUID"))
    document = serializers.CharField(help_text=_("Base 64 encoded document content."))

    def validate_document(self, value):
        try:
            # If validate is False, no check is done to see if the data contains non base-64 alphabet characters
            b64decode(value, validate=True)
        except binascii.Error as e:
            if str(e) == "Incorrect padding":
                raise ValidationError(
                    _("The provided base64 data has incorrect padding"),
                    code="incorrect-base64-padding",
                )
            raise ValidationError(str(e), code="invalid-base64")
        except TypeError as exc:
            raise ValidationError(str(exc))

        return value
