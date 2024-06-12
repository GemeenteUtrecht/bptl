from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class ZacUserDetailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)
    firstName = serializers.CharField(required=True, allow_blank=True)
    lastName = serializers.CharField(required=True, allow_blank=True)
    username = serializers.CharField(required=True, allow_blank=False)
    name = serializers.SerializerMethodField()
    assignee = serializers.CharField(
        required=False, help_text=_("The assignee of the user task as set by Camunda.")
    )

    def get_name(self, obj):
        name = f"{obj['firstName']} {obj['lastName']}"
        name = name.strip(" ")
        if not name:
            return "Medewerker"
        else:
            return name


class ZaakDetailURLSerializer(serializers.Serializer):
    zaakDetailUrl = serializers.URLField(
        required=False,
        allow_blank=False,
        help_text=_("URL of the ZAAK detail page in the zaakafhandelcomponent."),
    )
    error = serializers.CharField(required=False)
    retry = serializers.IntegerField(required=False)


class CreatedProcessInstanceSerializer(serializers.Serializer):
    instanceId = serializers.UUIDField(
        help_text=_("The UUID of the process instance."),
        required=True,
    )
    instanceUrl = serializers.URLField(
        help_text=_("The URL of the process instance."), required=True
    )


class RecipientListSerializer(serializers.Serializer):
    recipientList = serializers.ListField(
        child=serializers.EmailField(
            help_text=_("Email address of recipient."), allow_blank=False
        ),
        help_text=_("List of recipients."),
    )
