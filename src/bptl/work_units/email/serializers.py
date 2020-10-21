import copy

from django.utils.translation import ugettext_lazy as _

from rest_framework import exceptions, serializers

from bptl.tasks.base import MissingVariable

VALID_TEMPLATE_CHOICES = {
    "generiek": "email/mails/generic_email.txt",
    "accordering": "email/mails/review.txt",
    "advies": "email/mails/review.txt",
}


class EmailPersonSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)


class ContextSerializer(serializers.Serializer):
    kownslFrontendUrl = serializers.CharField(required=False)
    reminder = serializers.BooleanField(required=False)
    deadline = serializers.DateField(required=False)


class EmailSerializer(serializers.Serializer):
    subject = serializers.CharField(required=True)
    content = serializers.CharField(required=True, allow_blank=True)


class SendEmailSerializer(serializers.Serializer):
    sender = EmailPersonSerializer(required=True)
    receiver = EmailPersonSerializer(required=True)
    email = EmailSerializer(required=True)
    template = serializers.ChoiceField(
        choices=[(key, key) for key in VALID_TEMPLATE_CHOICES],
        required=True,
    )
    context = ContextSerializer(required=True)

    def is_valid(self, raise_exception=False):
        codes_to_catch = (
            "code='required'",
            "code='invalid_choice'",
            "code='blank'",
        )

        try:
            valid = super().is_valid(raise_exception=raise_exception)
            return valid
        except Exception as e:
            if isinstance(e, exceptions.ValidationError):
                error_codes = str(e.detail)
                if any(code in error_codes for code in codes_to_catch):
                    raise MissingVariable(e.detail)
            else:
                raise e
