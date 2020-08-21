from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from rest_framework import serializers

# Documentation: https://apidocs.validsign.nl/validsign_integrator_guide.pdf, p144


class EventTypes(DjangoChoices):
    DOCUMENT_SIGNED = ChoiceItem("DOCUMENT_SIGNED")
    EMAIL_BOUNCE = ChoiceItem("EMAIL_BOUNCE")
    KBA_FAILURE = ChoiceItem("KBA_FAILURE")
    PACKAGE_ACTIVATE = ChoiceItem("PACKAGE_ACTIVATE")
    PACKAGE_ARCHIVE = ChoiceItem("PACKAGE_ARCHIVE")
    PACKAGE_ATTACHMENT = ChoiceItem("PACKAGE_ATTACHMENT")
    PACKAGE_COMPLETE = ChoiceItem("PACKAGE_COMPLETE")
    PACKAGE_CREATE = ChoiceItem("PACKAGE_CREATE")
    PACKAGE_DEACTIVATE = ChoiceItem("PACKAGE_DEACTIVATE")
    PACKAGE_DECLINE = ChoiceItem("PACKAGE_DECLINE")
    PACKAGE_DELETE = ChoiceItem("PACKAGE_DELETE")
    PACKAGE_EXPIRE = ChoiceItem("PACKAGE_EXPIRE")
    PACKAGE_OPT_OUT = ChoiceItem("PACKAGE_OPT_OUT")
    PACKAGE_READY_FOR_COMPLETE = ChoiceItem("PACKAGE_READY_FOR_COMPLETE")
    PACKAGE_RESTORE = ChoiceItem("PACKAGE_RESTORE")
    PACKAGE_TRASH = ChoiceItem("PACKAGE_TRASH")
    ROLE_REASSIGN = ChoiceItem("ROLE_REASSIGN")
    SIGNER_COMPLETE = ChoiceItem("SIGNER_COMPLETE")
    SIGNER_LOCKED = ChoiceItem("SIGNER_LOCKED")
    TEMPLATE_CREATE = ChoiceItem("TEMPLATE_CREATE")


class CallbackSerializer(serializers.Serializer):
    name = serializers.ChoiceField(label=_("event"), choices=EventTypes)
    session_user = serializers.CharField()
    package_id = serializers.CharField(label=_("package ID"))
    document_id = serializers.CharField(
        label=_("document ID"), required=False, allow_null=True
    )
    new_role_id = serializers.CharField(
        label=_("new role ID"), required=False, allow_null=True
    )
    message = serializers.CharField(label=_("message"), required=False, allow_null=True)
    created_date = serializers.DateTimeField(label=_("created"))
