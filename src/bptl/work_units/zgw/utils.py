from urllib.parse import parse_qs, urlparse

from zds_client import Client


def get_paginated_results(
    client: Client, resource: str, minimum=None, *args, **kwargs
) -> list:
    query_params = kwargs.get("query_params", {})

    results = []
    response = client.list(resource, *args, **kwargs)

    results += response["results"]

    if minimum and len(results) >= minimum:
        return results

    while response["next"]:
        next_url = urlparse(response["next"])
        query = parse_qs(next_url.query)
        new_page = int(query["page"][0])
        query_params["page"] = [new_page]
        kwargs["query_params"] = query_params
        response = client.list(resource, *args, **kwargs)
        results += response["results"]

        if minimum and len(results) >= minimum:
            return results

    return results
