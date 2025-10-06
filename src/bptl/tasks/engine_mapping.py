from bptl.camunda.models import ExternalTask
from bptl.crontask.models import CronTask
from bptl.openklant.models import OpenKlantInternalTaskModel

from .constants import EngineTypes

ENGINETYPE_MODEL_MAPPING = {
    EngineTypes.camunda: ExternalTask,
    EngineTypes.openklant: OpenKlantInternalTaskModel,
    EngineTypes.crontask: CronTask,
}
