from typing import List

from rest_framework import exceptions
from zgw_consumers.concurrent import parallel

from bptl.tasks.base import MissingVariable, WorkUnit, check_variable
from bptl.tasks.registry import register

from .client import get_client, require_zac_service
from .serializers import ZacUserDetailSerializer


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
        usernames = []
        groupnames = []
        emails = []
        try:
            assignees = check_variable(variables, "usernames")
            for assignee in assignees:
                # To not change normal expected behavior:
                # if no emailNotificationList is found in variables everybody gets an email
                if email_notification_list.get(assignee) or not email_notification_list:
                    group_or_user, name = assignee.split(":", 1)
                    if group_or_user.lower() == "group":
                        groupnames.append(name)
                    else:
                        usernames.append(name)

        except MissingVariable:
            try:
                emails = check_variable(variables, "emailaddresses")
            except MissingVariable:
                raise MissingVariable(
                    "Missing one of the required variables usernames or emailaddresses."
                )

        users = []
        with get_client(self.task) as client:
            if usernames:
                username_assignees = client.get(
                    "api/accounts/users", params={"include_username": usernames}
                )
                for user in username_assignees["results"]:
                    user["assignee"] = f'user:{user["username"]}'
                users += username_assignees["results"]

            if groupnames:
                groups = {}

                def _get_group_users(group: str):
                    nonlocal groups, client
                    groups[group] = client.get(
                        "api/accounts/users", params={"include_groups": [group]}
                    )

                with parallel() as executor:
                    list(executor.map(_get_group_users, groupnames))
                for group, groupusers in groups.items():
                    for user in groupusers["results"]:
                        user["assignee"] = f"group:{group}"

                    users += groupusers["results"]

            if emails:
                users += client.get(
                    "api/accounts/users", params={"include_email": emails}
                )["results"]

        return users

    def validate_data(self, data: dict) -> dict:
        serializer = ZacUserDetailSerializer(data=data, many=True)
        codes_to_catch = (
            "code='required'",
            "code='blank'",
        )

        try:
            serializer.is_valid(raise_exception=True)
            return serializer.data
        except Exception as e:
            if isinstance(e, exceptions.ValidationError):
                error_codes = str(e.detail)
                if any(code in error_codes for code in codes_to_catch):
                    raise MissingVariable(e.detail)
            else:
                raise e

    def perform(self) -> dict:
        users = self.get_client_response()
        validated_data = self.validate_data(users)
        return {
            "userData": validated_data,
        }
