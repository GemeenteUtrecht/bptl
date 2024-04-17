from django.utils.translation import gettext_lazy as _

from celery.utils.log import get_task_logger
from django_camunda.tasks import start_process
from django_camunda.utils import serialize_variable
from rest_framework import exceptions, serializers
from zgw_consumers.api_models.constants import RolOmschrijving
from zgw_consumers.constants import APITypes

from bptl.tasks.base import MissingVariable, check_variable
from bptl.tasks.registry import register
from bptl.work_units.zgw.tasks.base import ZGWWorkUnit, require_zrc, require_ztc
from bptl.work_units.zgw.utils import get_paginated_results

from ..objects.client import require_objects_service
from ..objects.services import fetch_start_camunda_process_form

logger = get_task_logger(__name__)


class CreatedProcessInstanceSerializer(serializers.Serializer):
    instance_id = serializers.UUIDField(
        help_text=_("The UUID of the process instance."),
        read_only=True,
    )
    instance_url = serializers.URLField(
        help_text=_("The URL of the process instance."), read_only=True
    )


@register
@require_objects_service
@require_zrc
@require_ztc
class StartCamundaProcessTask(ZGWWorkUnit):
    """
    Starts the related camunda business process for a ZAAK if
    its ZAAKTYPE is associated to a configured StartCamundaProcessForm
    in the OBJECTS API.

    **Required process variables**
    * ``zaakUrl`` [str]: URL-reference of a ZAAK in Open Zaak.
    * ``bptlAppId`` [str]: the application ID of the app that caused this task to be executed.

    **Sets the process variables**

    * Does not set any process variables.

    """

    def validate_data(self, data: dict) -> dict:
        serializer = CreatedProcessInstanceSerializer(data=data)
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

    def perform(self) -> None:
        variables = self.task.get_variables()

        zrc_client = self.get_client(APITypes.zrc)
        zaak_url = check_variable(variables, "zaakUrl")
        zaak = zrc_client.retrieve("zaak", url=zaak_url)

        ztc_client = self.get_client(APITypes.ztc)
        zaaktype = ztc_client.retrieve("zaaktype", url=zaak["zaaktype"])
        catalogus = ztc_client.retrieve("catalogus", url=zaaktype["catalogus"])

        # If no form is found - return here
        form = fetch_start_camunda_process_form(
            self.task,
            zaaktype_identificatie=zaaktype["identificatie"],
            catalogus_domein=catalogus["domein"],
        )
        if not form:
            logger.warning(
                "Did not find a start camunda process form for zaaktype {zt}.".format(
                    zt=zaaktype["identificatie"]
                )
            )
            return {}

        set_variables = {
            "bptlAppId": serialize_variable(check_variable(variables, "bptlAppId")),
            "zaakUrl": serialize_variable(zaak["url"]),
            "zaakIdentificatie": serialize_variable(zaak["identificatie"]),
            "zaakDetails": serialize_variable(
                {
                    "omschrijving": zaak["omschrijving"],
                    "zaaktypeOmschrijving": zaaktype["omschrijving"],
                    "toelichting": zaak["toelichting"],
                }
            ),
        }

        initiator = variables.get("initiator", None)

        if not initiator:
            rollen = get_paginated_results(
                zrc_client, "rol", query_params={"zaak": zaak["url"]}
            )
            _rol = [
                rol
                for rol in rollen
                if rol["omschrijvingGeneriek"] == RolOmschrijving.initiator
            ]
            if _rol:  # THERE CAN BE ONLY ONE
                initiator = _rol[0]["betrokkeneIdentificatie"]["identificatie"]

        if initiator:
            set_variables["initiator"] = serialize_variable(initiator)

        results = start_process(
            process_key=form["camundaProcessDefinitionKey"],
            variables=set_variables,
        )
        self.validate_data(results)
        return {}
