from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from bptl.work_units.xential.utils import Base64Document


class CallbackDataSerializer(serializers.Serializer):
    bptl_ticket_uuid = serializers.UUIDField(label=_("BPTL ticket UUID"))
    document = Base64Document(help_text=_("Base 64 encoded document content."))
