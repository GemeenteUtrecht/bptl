from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class AssigneeTypeChoices(DjangoChoices):
    user = ChoiceItem("user", _("User"))
    group = ChoiceItem("group", _("Group"))
