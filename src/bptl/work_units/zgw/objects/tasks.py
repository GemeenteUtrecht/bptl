import datetime
import logging
from typing import Dict

from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes

from bptl.tasks.base import check_variable
from bptl.tasks.registry import register
from bptl.work_units.zgw.tasks.base import ZGWWorkUnit, require_zrc, require_ztc

from .client import require_objects_service, require_objecttypes_service
from .services import (
    create_object,
    fetch_checklist,
    fetch_checklist_objecttype,
    fetch_checklisttype,
)

logger = logging.getLogger(__name__)


@register
@require_objects_service
@require_objecttypes_service
@require_zrc
@require_ztc
class InitializeChecklistTask(ZGWWorkUnit):
    """
    Creates an empty CHECKLIST for ZAAK if CHECKLISTTYPE for ZAAKTYPE exists.

    **Required process variables**
    * ``zaakUrl`` [str]: URL-reference of a ZAAK in Open Zaak.
    * ``zaaktypeCatalogus`` [str]: URL-reference of a CATALOGUS in Open Zaak.
    * ``zaaktypeIdentificatie`` [str]: URL-reference of ZAAKTYPE in CATALOGUS of Open Zaak.

    **Sets the process variables**

    * ``initializedChecklist`` [bool]: Boolean that indicates whether an empty checklist was created.

    """

    def check_if_checklisttype_exists(self, variables: Dict) -> bool:
        # Check if checklisttype exists
        catalogus_url = check_variable(variables, "zaaktypeCatalogus")
        ztc_client = self.get_client(APITypes.ztc)
        catalogus = ztc_client.retrieve("catalogus", url=catalogus_url)
        catalogus_domein = catalogus["domein"]
        zaaktype_identificatie = check_variable(variables, "zaaktypeIdentificatie")
        checklisttype = fetch_checklisttype(
            self.task, catalogus_domein, zaaktype_identificatie
        )
        if not checklisttype:
            logger.warning(
                "CHECKLISTTYPE not found for ZAAKTYPE with identificatie: `{ztid}` in CATALOGUS with domein: `{domein}`.".format(
                    ztid=zaaktype_identificatie, domein=catalogus_domein
                )
            )
            return True
        return False

    def check_if_checklist_exists(self, variables: Dict) -> bool:
        # Check if checklist already exists
        zaak_url = check_variable(variables, "zaakUrl")
        checklist = fetch_checklist(self.task, zaak_url)
        if checklist:
            logger.warning("CHECKLIST already exists for ZAAK.")
            return True
        return False

    def perform(self) -> dict:
        variables = self.task.get_variables()
        with parallel() as executor:
            checks = list(
                executor.map(
                    lambda func: func(variables),
                    [
                        self.check_if_checklisttype_exists,
                        self.check_if_checklist_exists,
                    ],
                )
            )
        if any(checks):
            return {"initializedChecklist": False}

        zaak_url = check_variable(variables, "zaakUrl")
        latest_version = fetch_checklist_objecttype(self.task)
        record = {
            "answers": [],
            "meta": True,
            "zaak": zaak_url,
            "lockedBy": None,
        }
        data = {
            "type": latest_version["objectType"],
            "record": {
                "typeVersion": latest_version["version"],
                "data": record,
                "startAt": datetime.date.today().isoformat(),
            },
        }
        obj = create_object(self.task, data)
        relation_data = {
            "zaak": zaak_url,
            "object": obj["url"],
            "object_type": "overige",
            "object_type_overige": latest_version["jsonSchema"]["title"],
            "object_type_overige_definitie": {
                "url": latest_version["url"],
                "schema": ".jsonSchema",
                "objectData": ".record.data",
            },
            "relatieomschrijving": "Checklist van Zaak",
        }
        client = self.get_client(APITypes.zrc)
        client.create("zaakobject", relation_data)
        return {"initializedChecklist": True}
