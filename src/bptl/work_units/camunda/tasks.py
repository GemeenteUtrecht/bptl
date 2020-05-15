from django_camunda.client import get_client
from django_camunda.tasks import start_process

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.registry import register


class CamundaRequired(Exception):
    pass


@register
class CallActivity(WorkUnit):
    """
    Start subprocess in Camunda

    **Required process variables**

    * ``subprocessDefinitionId``: id of process definition for target subprocess.

    **Optional process variables (Camunda exclusive)**

    * ``variablesMapping``: JSON object to map variables from the parent process
       to be sent into the new subprocess. If renaming is not needed, use the same
       name as a key and a value. If ``variableMapping`` is empty, the all parent
       variables are sent to subprocess unchanged.

        .. code-block:: json

          {
              "<source variable name>": "<target variable name>",
          }

    **Sets the process variables**

    * ``processInstanceId``: instance id of the created subprocess
    """

    @staticmethod
    def construct_variables(source_vars, mapping) -> dict:
        if not mapping:
            return source_vars

        target_vars = {}
        for source, target in mapping.items():
            if source in source_vars:
                target_vars[target] = source_vars[source]

        return target_vars

    def perform(self) -> dict:
        variables = self.task.get_variables()
        subprocess_id = check_variable(variables, "subprocessDefinitionId")
        mapping = variables.get("variableMapping", {})

        # get parent process instance variables
        if not isinstance(self.task, ExternalTask):
            raise CamundaRequired("Only Camunda tasks support CallActivity task")
        instance_id = self.task.get_process_instance_id()
        camunda = get_client()
        instance_variables = camunda(f"process-instance/{instance_id}/variables")

        variables = self.construct_variables(instance_variables, mapping)

        # start subprocess
        subprocess = start_process(process_id=subprocess_id, variables=variables)

        return {"processInstanceId": subprocess["instance_id"]}
