from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class Statuses(DjangoChoices):
    initial = ChoiceItem("initial", _("Initial"))
    in_progress = ChoiceItem("in_progress", _("In progress"))
    performed = ChoiceItem("performed", _("Performed"))
    failed = ChoiceItem("failed", _("Failed"))
    completed = ChoiceItem("completed", _("Completed"))
