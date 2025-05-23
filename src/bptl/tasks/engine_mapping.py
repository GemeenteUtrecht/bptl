from bptl.activiti.models import ServiceTask
from bptl.camunda.models import ExternalTask
from bptl.openklant.models import OpenKlantInternalTaskModel

from .constants import EngineTypes

ENGINETYPE_MODEL_MAPPING = {
    EngineTypes.camunda: ExternalTask,
    EngineTypes.activiti: ServiceTask,
    EngineTypes.openklant: OpenKlantInternalTaskModel,
}
