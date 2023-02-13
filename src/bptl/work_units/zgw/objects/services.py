import logging
from typing import Dict, List, Optional

from django.utils.translation import ugettext_lazy as _

from bptl.core.models import CoreConfig
from bptl.tasks.models import BaseTask

from .client import get_objects_client
from .models import MetaObjectTypesConfig

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")


def fetch_objecttypes() -> List[dict]:
    config = CoreConfig.get_solo()
    service = config.primary_objecttypes_api
    client = service.build_client()
    return client.list("objecttype")


def search_objects(task, filters: Dict) -> List[dict]:
    client = get_objects_client(task)
    return client.operation("object_search", path="objects/search", data=filters)


def _search_meta_objects(
    task: BaseTask,
    attribute_name: str,
    zaaktype: Dict,
    catalogus: Dict,
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
    if not zaaktype:
        raise RuntimeError("ZAAKTYPE must be provided.")

    if not catalogus:
        raise RuntimeError("CATALOGUS must be provided.")

    object_filters["data_attrs"] += [
        f"zaaktypeIdentificaties__icontains__{zaaktype['identificatie']}",
        f"zaaktypeCatalogus__exact__{catalogus['domein']}",
    ]
    object_filters["data_attrs"] = ",".join(object_filters["data_attrs"])
    meta_objects = search_objects(task, object_filters)

    if not meta_objects:
        logger.warning("No `{url}` object is found.".format(url=ot_url))

    # there can be only one form per zaaktype
    if len(meta_objects) > 1:
        logger.warning("More than 1 `{url}` object is found.".format(url=ot_url))

    return meta_objects


###################################################
#               StartCamundaProces                #
###################################################


def fetch_start_camunda_process_form(
    task: BaseTask, zaaktype: Dict, catalogus: Dict
) -> Optional[Dict]:
    start_camunda_process_form = _search_meta_objects(
        task,
        "start_camunda_process_form_objecttype",
        zaaktype,
        catalogus,
    )
    if not start_camunda_process_form:
        return None

    return start_camunda_process_form[0]["record"]["data"]
