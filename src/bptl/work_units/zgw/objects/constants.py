from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advice"))
    approval = ChoiceItem("approval", _("Approval"))
