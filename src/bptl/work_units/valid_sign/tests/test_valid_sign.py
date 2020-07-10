from django.conf import settings
from django.test import TestCase

import requests
import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.work_units.valid_sign.tasks import ValidSignTask

ZRC_URL = "https://some.zrc.nl/api/v1/"
DOCUMENT_1 = (
    f"{ZRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891/"
)
DOCUMENT_2 = (
    f"{ZRC_URL}enkelvoudiginformatieobjecten/b7218c76-7478-41e9-a088-54d2f914a713/"
)
CONTENT_1 = f"{DOCUMENT_1}download/"
CONTENT_2 = f"{DOCUMENT_2}download/"

RESPONSE_1 = {
    "url": DOCUMENT_1,
    "uuid": "4f8b4811-5d7e-4e9b-8201-b35f5101f891",
    "inhoud": f"{DOCUMENT_1}download/",
    "titel": "Test Doc 1",
}


RESPONSE_2 = {
    "url": DOCUMENT_2,
    "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
    "inhoud": f"{DOCUMENT_2}download/",
    "titel": "Test Doc 2",
}


def mock_document_1_get(m):
    m.get(DOCUMENT_1, json=RESPONSE_1)


def mock_document_2_get(m):
    m.get(DOCUMENT_2, json=RESPONSE_2)


def mock_content_1_get(m):
    m.get(CONTENT_1, content=b"Test content 1")


def mock_content_2_get(m):
    m.get(CONTENT_2, content=b"Test content 2")


@requests_mock.Mocker(
    real_http=True
)  # Real HTTP used to test real requests to ValidSign
class ValidSignTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="validsign",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                # TODO create test data
                "documents": {"type": "List", "value": [DOCUMENT_1, DOCUMENT_2]},
                "signers": {"type": "String", "value": ""},
            },
        )

    def tearDown(self) -> None:
        super().tearDown()

        # Removing all packages from validsign
        get_url = f"{settings.VALIDSIGN_ROOT_URL}api/packages"
        headers = {
            "Accept": "*/*",
            "Authorization": f"Basic {settings.APIKEY}",
            "Content-Type": "application/json",
        }

        # This actually returns the data of the latest created package and the number of existing packages ...
        response = requests.get(get_url, headers=headers).json()
        number_of_packages = response.get("count")

        while number_of_packages > 0:
            package_id = response.get("results")[0].get("id")
            delete_url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package_id}"
            requests.delete(delete_url, headers=headers)
            response = requests.get(get_url, headers=headers).json()
            number_of_packages = response.get("count")

    # TODO
    def test_get_signers_info(self):
        pass

    # TODO
    def test_get_documents_info(self):
        pass

    # TODO
    def test_create_package(self, m):
        mock_document_1_get(m)
        mock_document_2_get(m)
        mock_content_1_get(m)
        mock_content_2_get(m)

        task = ValidSignTask(self.fetched_task)
        result = task.perform()

    # TODO
    def test_add_documents_to_package(self):
        pass

    # TODO
    def test_create_approval(self):
        pass

    # TODO
    def test_get_signing_urls(self):
        pass
