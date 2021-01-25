from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class TicketUuidSerializer(serializers.Serializer):
    bptl_ticket_uuid = serializers.UUIDField(label=_("BPTL ticket UUID"))
