from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register

from .client import get_client, require_xential_service


@register
@require_xential_service
def start_xential_template(task: BaseTask) -> dict:
    """
    Run Xential template with requested variables.
    The returned value is either buildId of created document (in case it is a silent template)
    or the url to the page where the user can manually fill in the input fields (in case it is
    an interactive template).

    In the task binding, the service with alias ``xential`` must be connected, so that
    this task knows which endpoints to contact.

    **Required process variables**

    * ``bptlAppId``: the application ID in the BPTL credential store
    * ``nodeRef``: a parameter to build POST url in Xential.
    * ``templateUuid``: the id of the template which should be started
    * ``filename``: the name of the generated document
    * ``templateVariables``: a JSON-object containing meta-data about the result:

      .. code-block:: json

         {
            "variable1": "String",
            "variable2": "String"
         }

    **Sets the process variables**

    * ``buildId``: the id of the generated document (in case of starting a silent template)
    * ``xentialTemplateUrl``: the url of the page with the form to fill in (in case of starting
    an interactive template)
    """
    variables = task.get_variables()
    node_ref = check_variable(variables, "nodeRef")
    template_uuid = check_variable(variables, "templateUuid")
    file_name = check_variable(variables, "filename")
    template_variables = (
        check_variable(variables, "templateVariables", empty_allowed=True) or {}
    )

    xential_client = get_client(task)

    # get sessionID
    list_url = "xential/templates"
    list_response = xential_client.get(list_url)
    session_id = list_response["data"]["params"]["sessionId"]

    # start template
    data = {
        "templateUuid": template_uuid,
        "sessionId": session_id,
        "filename": file_name,
        "variables": template_variables,
    }

    start_response = xential_client.post(
        "xential/templates/start",
        params={"nodeRef": node_ref},
        json=data,
    )

    return {
        "buildId": start_response.get("buildId"),
        "xentialTemplateUrl": start_response.get("xentialTemplateUrl"),
    }
