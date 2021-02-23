from requests import Response

from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.registry import register

from .client import get_client, require_zac_service
from .serializers import ZacUsersDetailsSerializer


@register
@require_zac_service
class UserDetailsTask(WorkUnit):
    """
    Requests email and name data from usernames from the zac.

    In the camunda process models accorderen/adviseren we have a list of usernames from
    the zac. In order to send signaling emails, we will need to fetch
    the email addresses and names from the zac and feed it back to the camunda process.

    In this first implementation a simple and direct get request is done
    at the zac.accounts.api endpoint.

    **Required process variables**

    * ``usernames``: JSON with usernames.
        .. code-block:: json

                [
                    "user1",
                    "user2",
                    "user3",
                ]

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets the process variables**

    * ``userData``: a JSON-object containing a list of user names and emails:

      .. code-block:: json

            [
                {
                    "name": "FirstName LastName",
                    "email": "test@test.nl"
                }
            ]

    """

    def get_client_response(self) -> Response:
        variables = self.task.get_variables()
        usernames = check_variable(variables, "usernames")
        params = {"include": usernames}
        with get_client(self.task) as client:
            return client.get("api/accounts/users", params=params)

    def validate_data(self, data: dict) -> dict:
        serializer = ZacUsersDetailsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    def perform(self) -> dict:
        response = self.get_client_response()
        validated_data = self.validate_data(response)
        return {
            "userData": validated_data["results"],
        }
