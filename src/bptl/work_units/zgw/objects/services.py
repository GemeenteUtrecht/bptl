import logging
from typing import Dict, List, Optional, Tuple

from django.http import Http404
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from zgw_consumers.concurrent import parallel

from bptl.core.utils import fetch_next_url_pagination
from bptl.tasks.base import check_variable
from bptl.tasks.models import BaseTask
from bptl.work_units.zgw.utils import get_paginated_results

from .client import ObjectsClient, get_objects_client, get_objecttypes_client
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


def fetch_objecttypes(task: BaseTask, query_params: dict = dict()) -> List[Dict]:
    client = get_objecttypes_client(task)
    objecttypes = get_paginated_results(
        client,
        "objecttypes",
        request_kwargs={"params": query_params},
    )
    return objecttypes


def fetch_object(
    object_url: str,
    client: Optional[ObjectsClient] = None,
    task: Optional[BaseTask] = None,
) -> Dict:
    if not client and not task:
        raise RuntimeError(
            "fetch_object requires one of keyword arguments client or task."
        )

    if task:
        client = get_objects_client(task)

    return client.get(
        path=object_url.split(client.api_root)[-1], operation="object_read"
    )


def fetch_objects(task: BaseTask, objects: List[str]) -> List[Dict]:
    client = get_objects_client(task)

    def _fetch_object(object_url):
        return fetch_object(client, object_url)

    with parallel() as executor:
        objects = list(executor.map(_fetch_object, objects))
    return objects


def update_object_record_data(
    task: BaseTask, object: Dict, data: Dict, username: Optional[str] = None
) -> Dict:
    client = get_objects_client(task)
    new_data = {
        "record": {
            **object["record"],
            "data": data,
            "correctionFor": object["record"]["index"],
            "correctedBy": username if username else "service-account",
        }
    }
    obj = client.operation(
        "object_partial_update",
        path="objects/" + object["uuid"],
        data=new_data,
        method="PATCH",
    )
    return obj


def search_objects(
    task: BaseTask, filters: Dict, query_params: Optional[Dict]
) -> Tuple[List[dict], Dict]:
    client = get_objects_client(task)
    response = client.operation(
        "object_search",
        path="objects/search",
        data=filters,
        request_kwargs={"params": query_params},
    )
    query_params = fetch_next_url_pagination(response, query_params)
    return response, query_params


def _search_meta_objects(
    task: BaseTask,
    attribute_name: str,
    unique: bool = False,
    data_attrs: Optional[List] = None,
) -> List[dict]:
    config = MetaObjectTypesConfig.get_solo()
    ot_url = getattr(config, attribute_name)
    if not ot_url:
        raise RuntimeError(
            "`{attr}` objecttype is not configured in core configuration or does not exist in the configured objecttype service.".format(
                attr=attribute_name
            )
        )

    if not data_attrs:
        logger.warning("Searching on `meta` objecttypes needs filtering.")
        return []

    object_filters = {"type": ot_url, "data_attrs": data_attrs}
    object_filters["data_attrs"] = ",".join(object_filters["data_attrs"])
    query_params = {"pageSize": 100}
    get_more = True
    meta_objects = []
    while get_more:
        response, query_params = search_objects(task, object_filters, query_params)
        meta_objects += response["results"]
        get_more = query_params.get("page", None)

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
    data_attrs = [
        f"zaaktypeIdentificaties__icontains__{zaaktype_identificatie}",
        f"zaaktypeCatalogus__exact__{catalogus_domein}",
    ]
    start_camunda_process_form = _search_meta_objects(
        task,
        "start_camunda_process_form_objecttype",
        data_attrs=data_attrs,
        unique=True,
    )
    if not start_camunda_process_form:
        return None

    return start_camunda_process_form[0]["record"]["data"]


###################################################
#                   Checklists                    #
###################################################


def fetch_checklist(
    task: BaseTask,
    zaak: str,
) -> Optional[Dict]:
    data_attrs = [f"zaak__icontains__{zaak}"]
    if objs := _search_meta_objects(
        task, "checklist_objecttype", data_attrs=data_attrs, unique=True
    ):
        return objs[0]
    return None


def fetch_checklist_objecttype(task: BaseTask):
    checklist_obj_type_url = MetaObjectTypesConfig.get_solo().checklist_objecttype
    checklist_obj_type = fetch_objecttype(task, checklist_obj_type_url)

    # Get latest version of objecttype
    return fetch_objecttype(task, max(checklist_obj_type["versions"]))


def fetch_checklisttype(
    task: BaseTask, catalogus_domein: str, zaaktype_identificatie: str
) -> Optional[Dict]:
    data_attrs = [
        f"zaaktypeIdentificaties__icontains__{zaaktype_identificatie}",
        f"zaaktypeCatalogus__exact__{catalogus_domein}",
    ]
    if checklisttypes := _search_meta_objects(
        task,
        "checklisttype_objecttype",
        data_attrs=data_attrs,
        unique=True,
    ):
        return checklisttypes[0]["record"]["data"]
    return None


###################################################
#            KOWNSL - review requests             #
###################################################


def fetch_review_request(task: BaseTask) -> Optional[Dict]:
    variables = task.get_variables()
    review_request_id = check_variable(variables, "kownslReviewRequestId")
    data_attrs = [f"id__exact__{review_request_id}"]
    if objs := _search_meta_objects(
        task, "review_request_objecttype", data_attrs=data_attrs, unique=True
    ):

        return objs[0]
    return None


def get_review_request(task: BaseTask) -> Optional[Dict]:
    if obj := fetch_review_request(task):
        return obj["record"]["data"]
    return None


def update_review_request(
    task: BaseTask,
    data: Dict = dict,
    requester: Optional[str] = None,
) -> Optional[Dict]:
    if rr := fetch_review_request(task):
        rr["record"]["data"] = {
            **rr["record"]["data"],
            **camelize(data, **api_settings.JSON_UNDERSCOREIZE),
        }
        result = update_object_record_data(
            task, rr, rr["record"]["data"], username=requester
        )
    else:
        raise Http404(
            _("Review request with for task: {task} could not be found..").format(
                task=str(task)
            )
        )

    return result["record"]["data"]


###################################################
#                KOWNSL - reviews                 #
###################################################


def fetch_reviews(
    task,
    review_request: Optional[str] = None,
    id: Optional[str] = None,
    zaak: Optional[str] = None,
    requester: Optional[str] = None,
) -> List[Dict]:

    data_attrs = []

    if review_request:
        data_attrs += [f"reviewRequest__exact__{review_request}"]
    if id:
        data_attrs += [f"id__exact__{id}"]
    if zaak:
        data_attrs += [f"zaak__exact__{zaak}"]
    if requester:
        data_attrs += [f"requester__exact__{requester}"]

    if objs := _search_meta_objects(
        task,
        "review_objecttype",
        data_attrs=data_attrs,
        unique=True if review_request or id else False,
    ):
        return objs

    return list()


def get_reviews_for_review_request(
    task: BaseTask,
) -> Optional[Dict]:
    variables = task.get_variables()
    review_request_id = check_variable(variables, "kownslReviewRequestId")
    reviews = fetch_reviews(task, review_request=review_request_id)
    if reviews:
        return reviews[0]["record"]["data"]
    return None
