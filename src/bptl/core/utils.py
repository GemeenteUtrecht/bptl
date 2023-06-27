from copy import deepcopy
from typing import Dict
from urllib.parse import parse_qs, urlparse


def fetch_next_url_pagination(response: Dict, query_params: Dict = dict()) -> Dict:
    query_params = deepcopy(query_params)
    if response["next"]:
        next_url = urlparse(response["next"])
        query = parse_qs(next_url.query)
        new_page = int(query["page"][0])
        query_params["page"] = [new_page]
    else:
        query_params["page"] = None
    return query_params
