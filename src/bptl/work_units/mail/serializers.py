from furl import furl
from rest_framework import exceptions, serializers

from bptl.tasks.base import MissingVariable

VALID_TEMPLATE_CHOICES = {
    "generiek": {
        "html": "mails/generic_email.html",
        "plain": "mails/generic_email.txt",
    },
    "accordering": {
        "html": "mails/review.html",
        "plain": "mails/review.txt",
    },
    "advies": {"html": "mails/review.html", "plain": "mails/review.txt"},
    "nen2580": {"html": "mails/nen2580.html", "plain": "mails/nen2580.txt"},
    "verzoek_afgehandeld": {
        "html": "mails/verzoek_afgehandeld.html",
        "plain": "mails/verzoek_afgehandeld.txt",
    },
}


class EmailPersonSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    assignee = serializers.CharField(required=False)


class ContextSerializer(serializers.Serializer):
    vraag = serializers.CharField(required=False)
    zaakIdentificatie = serializers.CharField(required=False)
    zaakOmschrijving = serializers.CharField(required=False)
    doReviewUrl = serializers.CharField(required=False)
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

    def validate(self, data):
        validated_data = super().validate(data)
        if (
            "doReviewUrl" in validated_data["context"]
            and "assignee" in validated_data["receiver"]
        ):
            url = furl(validated_data["context"]["doReviewUrl"])
            url.add({"assignee": validated_data["receiver"]["assignee"]})
            validated_data["context"]["doReviewUrl"] = url.url
        return validated_data

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
