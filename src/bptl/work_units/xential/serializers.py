from django.utils.translation import gettext_lazy as _

from drf_extra_fields.fields import Base64FileField
from rest_framework import serializers


class CallbackDataSerializer(serializers.Serializer):
    bptl_ticket_uuid = serializers.UUIDField(label=_("BPTL ticket UUID"))
    document = Base64FileField(help_text=_("Base 64 encoded document content."))
