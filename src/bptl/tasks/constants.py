from djchoices import ChoiceItem, DjangoChoices

from bptl.activiti.models import ServiceTask
from bptl.camunda.models import ExternalTask


class EngineTypes(DjangoChoices):
    camunda = ChoiceItem("camunda", "Camunda")
    activiti = ChoiceItem("activiti", "Activiti")


TASKTYPE_MAPPING = {
    EngineTypes.camunda: ExternalTask,
    EngineTypes.activiti: ServiceTask,
}
