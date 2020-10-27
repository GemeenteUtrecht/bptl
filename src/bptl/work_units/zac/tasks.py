import json

from requests import Response

from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.registry import register

from .client import ZACClient
from .serializers import ZacUsersDetailsSerializer


@register
class UserDetailsTask(WorkUnit):
    """
    Requests email and name data from usernames from the zac.

    In the camunda process models accorderen/adviseren we have a list of usernames from
    the zac. In order to send signaling emails, we will need to fetch
    the email addresses and names from the zac and feed it back to the camunda process.

    In this first implementation a simple and direct get request is done
    at the zac.accounts.api endpoint.

    The task requires the service with alias "zac" to be configured in the work_unit
    services and be registered in the ZAC where the token will be set.

    **Required process variables**

    * ``usernames``: JSON with usernames.
        .. code-block:: json
        
                [
                    "user1",
                    "user2",
                    "user3",
                ]

    **Sets the process variables**

    * ``userData``: a JSON-object containing a list of user names and emails:

      .. code-block:: json
      
            [
                {
                    "name": "FirstName LastName"
                    "email": "test@test.nl"
                }
            ]

    """

    def get_client_response(self) -> Response:
        client = ZACClient()
        variables = self.task.get_variables()
        usernames = check_variable(variables, "usernames")
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
        validated_data = json.dumps(validated_data["results"])
        return {
            "userData": json.loads(validated_data),
        }
