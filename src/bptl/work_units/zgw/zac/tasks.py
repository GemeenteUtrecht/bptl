import logging
from typing import List

from django.utils.translation import gettext_lazy as _

from requests.exceptions import HTTPError
from rest_framework import exceptions
from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes

from bptl.tasks.base import MissingVariable, WorkUnit, check_variable
from bptl.tasks.registry import register
from bptl.work_units.zgw.tasks.base import ZGWWorkUnit, require_zrc

from .client import get_client, require_zac_service
from .serializers import (
    RecipientListSerializer,
    ZaakDetailURLSerializer,
    ZacUserDetailSerializer,
)

logger = logging.getLogger(__name__)


@register
@require_zac_service
class UserDetailsTask(WorkUnit):
    """
    Requests email and name data from usernames from the zac
    and feeds them back to the camunda process.

    **Required process variables**

    * ``usernames`` [list[str]]: usernames.

        .. code-block:: json

                [
                    "user:user1",
                    "user:user2",
                    "group:group1"
                ]

    OR

    * ``emailaddresses`` [list[str]]: user email addresses.

        .. code-block:: json

                [
                    "user1@email",
                    "user2@email"
                ]

    **Optional process variables**

    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.
    * ``emailNotificationList``: JSON with email notification flags per "user".

    **Sets the process variables**

    * ``userData`` [list[json]]: a list of user names and emails:

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
            "userData": [*validated_data],
        }


@register
@require_zac_service
@require_zrc
class ZaakDetailURLTask(ZGWWorkUnit):
    """
    Requests the URL to the zaak detail page of a ZAAK in open zaak.

    **Required process variables**
    * ``zaakUrl`` [str]: URL-reference of a ZAAK in Open Zaak.

    **Sets the process variables**

    * ``zaakDetailUrl`` [str]: URL-reference to the ZAC ZAAK detail page.

    """

    def get_client_response(self) -> List[dict]:
        variables = self.task.get_variables()
        zaak_url = check_variable(variables, "zaakUrl")
        zrc_client = self.get_client(APITypes.zrc)

        try:
            zaak = zrc_client.retrieve("zaak", url=zaak_url)
            with get_client(self.task) as client:
                response = client.get(
                    f"api/core/cases/{zaak['bronorganisatie']}/{zaak['identificatie']}/url"
                )
        except HTTPError as exc:
            if (
                exc.response.status_code == 404
                and (retry := self.task.get_variables().get("retry", 0)) < 3
            ):
                response = {"error": "Zaak not found.", "retry": retry + 1}
            else:
                raise exc

        return response

    def validate_data(self, data: dict) -> dict:
        serializer = ZaakDetailURLSerializer(data=data)
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
        response = self.get_client_response()
        validated_data = self.validate_data(response)
        return validated_data


@register
@require_zac_service
class ZacEmailUserLogs(ZGWWorkUnit):
    """
    Requests the URL to the zaak detail page of a ZAAK in open zaak.

    **Required process variables**
    * ``recipientList`` List[str]: List of email adresses to sent email to.

    """

    def validate_data(self, data: dict) -> dict:
        check_variable(data, "recipientList", empty_allowed=False)
        serializer = RecipientListSerializer(data=data)
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
            raise e

    def perform(self) -> None:
        variables = self.task.get_variables()
        data = self.validate_data(variables)
        with get_client(self.task) as client:
            client.post(
                f"api/accounts/management/axes/logs",
                json=data,
            )
        return None
