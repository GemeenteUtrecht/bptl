from djchoices import ChoiceItem, DjangoChoices


class EngineTypes(DjangoChoices):
    camunda = ChoiceItem("camunda", "Camunda")
    activiti = ChoiceItem("activiti", "Activiti")
    openklant = ChoiceItem("openklant", "OpenKlant")
