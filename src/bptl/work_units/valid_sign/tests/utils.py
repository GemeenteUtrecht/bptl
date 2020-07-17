import json
import os
from typing import Optional

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "schemas",)


def mock_service_oas_get(
    m: Mocker, url: str, service: str, extension: Optional[str] = "yaml"
) -> None:
    file_name = f"{service}.{extension}"
    file = os.path.join(MOCK_FILES_DIR, file_name)
    oas_url = f"{url}schema/openapi.yaml?v=3"

    with open(file, "rb") as api_spec:
        api_data = api_spec.read()
        if extension == "json":
            m.get(oas_url, json=json.loads(api_data))
        else:
            m.get(oas_url, content=api_data)
