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
    startPeriod = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text=_("The start date of the logging period."),
    )
    endPeriod = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text=_("The end date of the logging period."),
    )

    def validate_recipientList(self, value):
        if not value:
            raise serializers.ValidationError(_("Recipient list cannot be empty."))
        return value

    def validate_startPeriod(self, value):
        if value and value > serializers.DateField().today():
            raise serializers.ValidationError(
                _("Start period cannot be in the future.")
            )
        return value

    def validate_endPeriod(self, value):
        if value and value > serializers.DateField().today():
            raise serializers.ValidationError(_("End period cannot be in the future."))
        return value

    def validate(self, data):
        if data.get("startPeriod") and data.get("endPeriod"):
            if data["startPeriod"] > data["endPeriod"]:
                raise serializers.ValidationError(
                    _("Start period cannot be after end period.")
                )
        return data


class VGUReportSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        help_text="Unique identifier of the ZAAK within bronorganisatie."
    )
    omschrijving = serializers.CharField(
        help_text="Omschrijving of the ZAAK.", allow_blank=True
    )
    zaaktype = serializers.CharField(help_text="Omschrijving of the ZAAKTYPE.")
    registratiedatum = serializers.DateField(
        help_text="Date at which the ZAAK was registered (YYYY-MM-DD)."
    )
    initiator = serializers.EmailField(
        help_text="The initiator of the ZAAK, if available.", allow_blank=True
    )
    objecten = serializers.CharField(
        help_text="A comma-separated list of OBJECTs related to ZAAK. If no OBJECTs are related, this field will be empty.",
        allow_blank=True,
    )
    aantalInformatieobjecten = serializers.IntegerField(
        help_text="The number of INFORMATIEOBJECTs related to the ZAAK."
    )
