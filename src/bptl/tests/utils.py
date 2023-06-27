from typing import Any, Dict, List

from zgw_consumers.concurrent import parallel


class mock_parallel(parallel):
    def map(self, fn, *iterables, timeout=None, chunksize=1):
        return map(fn, *iterables)


def paginated_response(results: List[dict]) -> Dict[str, Any]:
    body = {
        "count": len(results),
        "previous": None,
        "next": None,
        "results": results,
    }
    return body
