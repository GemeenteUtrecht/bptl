import os

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "schemas",
)

VALIDSIGN_API_DOCS = "https://apidocs.validsign.nl/validsign_openapi.yaml"


def mock_validsign_oas_get(m: Mocker):
    file = os.path.join(MOCK_FILES_DIR, "validsign.yaml")
    with open(file, "rb") as api_spec:
        m.get(VALIDSIGN_API_DOCS, content=api_spec.read())
