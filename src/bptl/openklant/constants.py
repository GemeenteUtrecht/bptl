from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class FailedTaskStatuses(DjangoChoices):
    initial = ChoiceItem("initial", _("Queued for retry"))
    failed = ChoiceItem("failed", _("Failed after retry"))
    succeeded = ChoiceItem("succeeded", _("Succeded after retry"))
