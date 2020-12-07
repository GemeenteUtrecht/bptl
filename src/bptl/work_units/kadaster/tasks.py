from typing import Any, Dict

from bptl.tasks.base import BaseTask, check_variable
from bptl.tasks.registry import register

from .utils import get_client, require_brt_service


@register
@require_brt_service
def retrieve_openbare_ruimten(task: BaseTask) -> Dict[str, Any]:
    """
    Given a bounding box (or other polygon), retrieve the 'public space' objects
    contained/overlapping.

    This consumes the BRT API to fetch relevant objects, which are returned so that they
    can be drawn/selected on maps as GeoJSON.

    Checked resources:

    - Wegdeel
    - Terrein (in development)
    - Inrichtingselement (in development)

    **Required process variables**

    * ``geometry``: A GeoJSON geometry that is checked for overlap.

    **Sets the following return/process variables**

    * ``features``: a list of GeoJSON features, in EPSG:4258 CRS. Properties contain
      feature-specific keys/values.

    .. note:: The kadaster geo query APIs have long response times (up to 40s) - this
       work unit takes a considerable time to execute.
    """
    variables = task.get_variables()
    geo = check_variable(variables, "geometry")

    resources = ["wegdelen"]  # , "inrichtingselementen"]
    formatters = {
        "wegdelen": format_wegdeel,
    }

    body = {"geometrie": {"intersects": geo}}
    headers = {
        "Accept-Crs": "epsg:4258",  # ~ WGS84
    }
    client = get_client()

    def fetch(resource: str, formatter: callable):
        resp_data = client.post(
            resource,
            params={"pageSize": 50},
            json=body,
            headers=headers,
        )
        results = resp_data["_embedded"][resource]
        results = [formatter(result) for result in results]
        return results

    features = [fetch(resource, formatters[resource]) for resource in resources]
    return {"features": features}


def format_wegdeel(wegdeel: Dict[str, Any]) -> Dict[str, str]:
    return {
        "type": "Feature",
        "geometry": wegdeel["_embedded"]["hoofdGeometrie"],
        "properties": {
            "url": wegdeel["_links"]["self"]["href"],
            "objectType": "wegdeel",
            "identificatie": wegdeel["identificatie"],
            "status": wegdeel["status"],
            "naam": wegdeel["naam"],
        },
    }
