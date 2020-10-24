import json

from requests import Response

from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.registry import register

from .client import ZACClient
from .serializers import ZacUsersDetailsSerializer


@register
class UserDetailsTask(WorkUnit):
    """
    In the camunda process model we have a list of usernames from
    the zac. In order to send the emails, we will need to fetch
    the email addresses and names from the zac and feed it back to the camunda process.

    In this first implementation a simple and direct get request is done
    at the zac.accounts.api endpoint.

    In following iterations we will have to make use of OAS or maybe
    communicate through camunda.

    This task requests email and name data from usernames from the zac.

    **Required process variables**

    * ``usernames``: JSON with usernames.
        .. code-block:: json
                [
                    "thor",
                    "loki",
                    "odin",
                ]
    """

    def get_client_response(self) -> Response:
        client = ZACClient()
        variables = self.task.get_variables()
        usernames = check_variable(variables, "kownslUsers")
        url = f"accounts/api/users?filter_users={','.join(usernames)}&include=True"
        response = client.get(url)
        return response

    def validate_data(self, data: dict) -> dict:
        serializer = ZacUsersDetailsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    def perform(self) -> dict:
        response = self.get_client_response()
        validated_data = self.validate_data(response.json())
        return json.dumps(validated_data["results"])
