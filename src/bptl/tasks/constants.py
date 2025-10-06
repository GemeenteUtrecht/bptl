from djchoices import ChoiceItem, DjangoChoices


class EngineTypes(DjangoChoices):
    camunda = ChoiceItem("camunda", "Camunda")
    openklant = ChoiceItem("openklant", "OpenKlant")
    crontask = ChoiceItem("crontask", "CronTask")
