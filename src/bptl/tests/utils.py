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


def get_admin_form(page):
    """
    Return the main Django admin form on add/change pages,
    skipping logout/search forms that confuse django-webtest.
    """
    if "taskmapping_form" in page.forms:  # unlikely custom id
        return page.forms["taskmapping_form"]
    if "app_form" in page.forms:  # Django’s default admin add form id
        return page.forms["app_form"]
    # fall back to the first non-logout form
    for key, form in page.forms.items():
        if key != "logout-form":
            return form
    raise AssertionError(f"No usable admin form found in {list(page.forms.keys())}")
