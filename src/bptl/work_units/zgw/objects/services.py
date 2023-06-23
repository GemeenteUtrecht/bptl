import logging
from typing import Dict, List, Optional

from django.utils.translation import ugettext_lazy as _

from bptl.tasks.models import BaseTask

from .client import get_objects_client, get_objecttypes_client
from .models import MetaObjectTypesConfig

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")


def create_object(task: BaseTask, data: Dict) -> Dict:
    client = get_objects_client(task)
    return client.operation("object_create", path="objects", data=data)


def fetch_objecttype(task: BaseTask, url: str) -> Dict:
    client = get_objecttypes_client(task)
    assert client.api_root in url, f"Not the correct client for url {url}."
    path = url.split(client.api_root)[-1]
    return client.get(path)


def fetch_objecttypes(task: BaseTask, query_params: dict = dict) -> List[dict]:
    client = get_objecttypes_client(task)
    return client.get("objecttypes", params=query_params)


def search_objects(task: BaseTask, filters: Dict) -> List[Dict]:
    client = get_objects_client(task)
    return client.operation("object_search", path="objects/search", data=filters)


def _search_meta_objects(
    task: BaseTask,
    attribute_name: str,
    zaaktype_identificatie: str = "",
    catalogus_domein: str = "",
    zaak: str = "",
    unique: bool = False,
) -> List[dict]:
    config = MetaObjectTypesConfig.get_solo()
    ot_url = getattr(config, attribute_name)
    if not ot_url:
        raise RuntimeError(
            "`{attr}` objecttype is not configured in core configuration or does not exist in the configured objecttype service.".format(
                attr=attribute_name
            )
        )

    object_filters = {"type": ot_url, "data_attrs": ["meta__icontains__true"]}
    if (not zaaktype_identificatie or not catalogus_domein) and not zaak:
        logger.warning(
            "If ZAAK is not provided - zaaktype_identificatie and catalogus_domein MUST be provided."
        )
        return []

    if zaak:
        object_filters["data_attrs"] += [f"zaak__icontains__{zaak}"]
    else:
        object_filters["data_attrs"] += [
            f"zaaktypeIdentificaties__icontains__{zaaktype_identificatie}",
            f"zaaktypeCatalogus__exact__{catalogus_domein}",
        ]

    object_filters["data_attrs"] = ",".join(object_filters["data_attrs"])
    meta_objects = search_objects(task, object_filters)

    if not meta_objects:
        logger.warning("No `{url}` object is found.".format(url=ot_url))

    # there can be only one form/checklisttype per zaaktype
    if unique and len(meta_objects) > 1:
        logger.warning("More than 1 `{url}` object is found.".format(url=ot_url))

    return meta_objects


###################################################
#               StartCamundaProces                #
###################################################


def fetch_start_camunda_process_form(
    task: BaseTask, zaaktype_identificatie: str, catalogus_domein: str
) -> Optional[Dict]:
    start_camunda_process_form = _search_meta_objects(
        task,
        "start_camunda_process_form_objecttype",
        zaaktype_identificatie,
        catalogus_domein,
        unique=True,
    )
    if not start_camunda_process_form:
        return None

    return start_camunda_process_form[0]["record"]["data"]


###################################################
#                   Checklists                    #
###################################################


def fetch_checklist_object(
    task: BaseTask,
    zaak: str,
) -> Optional[Dict]:
    if objs := _search_meta_objects(
        task, "checklist_objecttype", zaak=zaak, unique=True
    ):
        return objs[0]
    return None


def fetch_checklist_objecttype(task: BaseTask):
    checklist_obj_type_url = MetaObjectTypesConfig.get_solo().checklist_objecttype
    checklist_obj_type = fetch_objecttype(task, checklist_obj_type_url)

    # Get latest version of objecttype
    return fetch_objecttype(task, max(checklist_obj_type["versions"]))


def fetch_checklist(task: BaseTask, zaak: str) -> Optional[Dict]:
    checklist_object_data = fetch_checklist_object(task, zaak)
    return checklist_object_data


def fetch_checklisttype_object(task: BaseTask) -> Optional[Dict]:
    """
    Cache the broader group of checklisttypes to increase performance
    related to fetching meta objects.

    The key relates to the field name on MetaObjectsConfig singletonmodel
    found in zac.core.models.

    """
    if objs := _search_meta_objects(task, "checklisttype_objecttype", unique=False):
        return objs
    return None


def fetch_checklisttype(
    task: BaseTask, catalogus_domein: str, zaaktype_identificatie: str
) -> Optional[Dict]:
    checklisttypes = fetch_checklisttype_object(task)
    if not checklisttypes:
        return None

    checklisttypes = [
        clt
        for clt in checklisttypes
        if zaaktype_identificatie in clt["record"]["data"]["zaaktypeIdentificaties"]
        and catalogus_domein in clt["record"]["data"]["zaaktypeCatalogus"]
    ]
    if not checklisttypes:
        return None

    if len(checklisttypes) > 1:
        logger.warning("More than 1 checklisttype_objecttype object is found.")

    return (checklisttypes[0]["record"]["data"],)
