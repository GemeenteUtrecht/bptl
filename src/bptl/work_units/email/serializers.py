from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from rest_framework import serializers


class ValidTemplateChoices(DjangoChoices):
    generiek = ChoiceItem("generiek", "../templates/generic_email.txt")
    accordering = ChoiceItem("accordering", "../templates/review.txt")
    advies = ChoiceItem("advies", "../templates/review.txt")


class EmailPersonSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)


class KwargsSerializer(serializers.Serializer):
    kownslFrontendUrl = serializers.CharField(required=False)
    reminder = serializers.BooleanField(required=False)
    deadline = serializers.DateTimeField(required=False)


class EmailSerializer(serializers.Serializer):
    subject = serializers.CharField(required=True)
    content = serializers.CharField(required=True)


class SendEmailSerializer(serializers.Serializer):
    sender = EmailPersonSerializer()
    receiver = EmailPersonSerializer()
    email = EmailSerializer()
    template = serializers.ChoiceField(
        choices=[key for key in ValidTemplateChoices.labels],
        required=True,
    )
    kwargs = KwargsSerializer()
