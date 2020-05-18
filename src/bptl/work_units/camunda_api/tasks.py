from django_camunda.api import get_all_process_instance_variables
from django_camunda.client import get_client
from django_camunda.tasks import start_process
from django_camunda.utils import serialize_variable

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.registry import register

__all__ = ["CallActivity"]


class CamundaRequired(Exception):
    pass


@register
class CallActivity(WorkUnit):
    """
    Start subprocess in Camunda

    **Required process variables**

    * ``subprocessDefinition``: process definition key for the target subprocess to
       start.

    **Optional process variables**

    * ``subprocessDefinitionVersion``: a specific version of the deployed subprocess.
       defaults to ``latest`` if not set, which means the process will be kicked off by
       definition key.

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
        subprocess_key = check_variable(variables, "subprocessDefinition")
        subprocess_version = variables.get("subprocessDefinitionVersion", "latest")
        mapping = variables.get("variablesMapping", {})

        if not isinstance(self.task, ExternalTask):
            raise CamundaRequired("Only Camunda tasks support CallActivity task")

        # get parent process instance variables
        instance_id = self.task.get_process_instance_id()
        instance_variables = get_all_process_instance_variables(instance_id)
        serialized_variables = {
            k: serialize_variable(v) for k, v in instance_variables.items()
        }

        variables = self.construct_variables(serialized_variables, mapping)

        # determine which process version
        if subprocess_version == "latest":
            start_process_kwargs = {"process_key": subprocess_key}
        else:
            client = get_client()
            definitions = client.get(
                "process-definition",
                params={"key": subprocess_key, "version": subprocess_version,},
            )
            if len(definitions) != 1:
                raise ValueError(
                    f"Expected 1 process definition for key {subprocess_key} and version "
                    f"{subprocess_version}, got {len(definitions)}."
                )
            start_process_kwargs = {"process_id": definitions[0]["id"]}

        # start subprocess
        subprocess = start_process(variables=variables, **start_process_kwargs)

        return {"processInstanceId": subprocess["instance_id"]}
