from django.utils.translation import ugettext_lazy as _
import copy 

from rest_framework import serializers


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
    deadline = serializers.DateTimeField(required=False)
    

class EmailSerializer(serializers.Serializer):
    subject = serializers.CharField(required=True)
    content = serializers.CharField(required=True)


class SendEmailSerializer(serializers.Serializer):
    sender = EmailPersonSerializer(required=True)
    receiver = EmailPersonSerializer(required=True)
    email = EmailSerializer(required=True)
    template = serializers.ChoiceField(
        choices=[(key, key) for key in VALID_TEMPLATE_CHOICES],
        required=True,
    )
    context = ContextSerializer(required=True)