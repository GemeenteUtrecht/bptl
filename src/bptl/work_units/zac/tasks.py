from typing import List

from bptl.tasks.base import MissingVariable, WorkUnit, check_variable
from bptl.tasks.registry import register

from .client import get_client, require_zac_service
from .serializers import ZacUsersDetailsSerializer


@register
@require_zac_service
class UserDetailsTask(WorkUnit):
    """
    Requests email and name data from usernames from the zac
    and feeds them back to the camunda process.

    **Required process variables**
    * ``usernames``: JSON with usernames.

        .. code-block:: json

                [
                    "user:user1",
                    "user:user2",
                    "group:group1"
                ]

    OR

    * ``emailaddresses``: JSON with email addresses.

        .. code-block:: json

                [
                    "user1@email",
                    "user2@email"
                ]

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.
    * ``emailNotificationList``: JSON with email notification flags per "user".

    **Sets the process variables**

    * ``userData``: a JSON-object containing a list of user names and emails:

      .. code-block:: json

            [
                {
                    "name": "FirstName LastName",
                    "username": "username",
                    "email": "test@test.nl"
                }
            ]

    """

    def get_client_response(self) -> List[dict]:
        variables = self.task.get_variables()
        email_notification_list = variables.get("emailNotificationList", {})
        try:
            assignees = check_variable(variables, "usernames")
            usernames = []
            groupnames = []
            for assignee in assignees:
                # To not change normal expected behavior:
                # if no emailNotificationList is found in variables everybody gets an email
                if email_notification_list.get(assignee) or not email_notification_list:
                    group_or_user, name = assignee.split(":", 1)
                    if group_or_user.lower() == "group":
                        groupnames.append(name)
                    else:
                        usernames.append(name)

            list_of_params = []
            if usernames:
                list_of_params.append({"include_username": usernames})
            if groupnames:
                list_of_params.append({"include_groups": groupnames})

        except MissingVariable:
            try:
                emails = check_variable(variables, "emailaddresses")
                list_of_params = [{"include_email": emails}]
            except MissingVariable:
                raise MissingVariable(
                    "Missing one of the required variables usernames or emailaddresses."
                )

        results = []
        with get_client(self.task) as client:
            for params in list_of_params:
                results.append(client.get("api/accounts/users", params=params))
        return results

    def validate_data(self, data: dict) -> dict:
        serializer = ZacUsersDetailsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    def perform(self) -> dict:
        results = self.get_client_response()
        validated_data = []
        for users in results:
            validated_data += self.validate_data(users)["results"]
        return {
            "userData": validated_data,
        }
