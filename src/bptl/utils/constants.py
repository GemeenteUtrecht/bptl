from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class Statuses(DjangoChoices):
    initial = ChoiceItem("initial", _("Initial"))
    in_progress = ChoiceItem("in_progress", _("In progress"))
    performed = ChoiceItem(
        "performed", _("The task is performed, but not sent to Camunda")
    )
    failed = ChoiceItem("failed", _("Failed"))
    completed = ChoiceItem("completed", _("Completed"))
