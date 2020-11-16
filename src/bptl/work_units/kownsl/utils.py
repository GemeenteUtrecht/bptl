from django.utils.translation import gettext_lazy as _

from zds_client.schema import get_operation_url
from zgw_consumers.client import ZGWClient
from zgw_consumers.constants import APITypes

from bptl.credentials.api import get_credentials
from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register
from bptl.work_units.zgw.client import (  # TODO: move exceptions to more generic place
    NoService,
)
from bptl.work_units.zgw.models import DefaultService

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
    operation_id = "reviewrequest_retrieve"
    url = get_operation_url(
        client.schema,
        operation_id,
        base_url=client.base_url,
        uuid=review_request_id,
    )
    review_request = client.request(url, operation_id)
    return review_request
