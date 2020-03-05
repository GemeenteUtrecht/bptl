from typing import Any, Dict

from bptl.tasks.models import BaseTask
from bptl.tasks.registry import register

API_ROOT = "https://brt.basisregistraties.overheid.nl/api/v2"


@register
def retrieve_openbare_ruimten(task: BaseTask) -> Dict[str, Any]:
    """
    Given a bounding box (or other polygon), retrieve the 'public space' objects
    contained/overlapping.

    This consumes the BRT API to fetch relevant objects, which are returned so that they
    can be drawn/selected on maps as GeoJSON.

    Checked resources:
    - Wegdeel
    - Terrein
    - Inrichtingselement

    **Required process variables**

    * ``geometry``: A GeoJSON geometry that is checked for overlap.
    * ``BRTKey``: API key to use to query the BRT
    """
    import bpdb

    bpdb.set_trace()
