from django.utils.translation import gettext_lazy as _

from zgw_consumers.client import ZGWClient
from zgw_consumers.constants import APITypes

from bptl.credentials.api import get_credentials
from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.models import DefaultService
from bptl.tasks.registry import register
from bptl.work_units.zgw.client import (  # TODO: move exceptions to more generic place
    NoService,
)

ALIAS = "kownsl"
PROCESS_VAR_NAME = "bptlAppId"

require_kownsl_service = register.require_service(
    APITypes.orc, description=_("The Kownsl instance to use."), alias=ALIAS
)


def get_client(task: BaseTask) -> ZGWClient:
    # find the configured service
    task_variables = task.get_variables()
    app_id = task_variables.get(PROCESS_VAR_NAME)
    topic_name = task.topic_name

    default_services = DefaultService.objects.filter(
        task_mapping__topic_name=topic_name, service__api_type=APITypes.orc, alias=ALIAS
    ).select_related("service")

    if not default_services:
        raise NoService(
            f"Topic '{topic_name}' is missing service with alias '{ALIAS}'."
        )

    service = default_services[0].service
    client = service.build_client()
    client._log.task = task
    client.operation_suffix_mapping = {
        **client.operation_suffix_mapping,
        "retrieve": "_retrieve",
    }

    # set the auth if we have the bptlAppId set
    if app_id:
        auth_headers = get_credentials(app_id, service)[service]
        if auth_headers:
            client.set_auth_value(auth_headers)

    return client


def get_review_request(task: BaseTask) -> dict:
    """
    Get a single review request from kownsl.
    """

    # Get variables
    variables = task.get_variables()

    # Build url
    client = get_client(task)
    review_request_id = check_variable(variables, "kownslReviewRequestId")
    review_request = client.retrieve("review_requests", uuid=review_request_id)
    return review_request
