from rest_framework import exceptions, serializers

from bptl.tasks.base import MissingVariable

VALID_TEMPLATE_CHOICES = {
    "generiek": "email/mails/generic_email.txt",
    "accordering": "email/mails/review.txt",
    "advies": "email/mails/review.txt",
    "nen2580": "email/mails/nen2580.txt",
    "verzoek_afgehandeld": "email/mails/verzoek_afgehandeld.txt",
}


class EmailPersonSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    assignee = serializers.CharField(required=False)


class ContextSerializer(serializers.Serializer):
    kownslFrontendUrl = serializers.CharField(required=False)
    deadline = serializers.DateField(format="%d-%m-%Y", required=False)
    reviewType = serializers.CharField(required=False)
    zaakDetailUrl = serializers.CharField(required=False)


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
