from bptl.activiti.models import ServiceTask
from bptl.camunda.models import ExternalTask

TASKTYPE_MAPPING = {"camunda": ExternalTask, "activiti": ServiceTask}
