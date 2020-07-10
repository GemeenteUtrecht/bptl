from django.conf import settings
from django.test import TestCase

import requests

from bptl.camunda.models import ExternalTask
from bptl.work_units.valid_sign.tasks import ValidSignTask


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
                "documents": [""],
                "signers": [""],
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
    def test_create_package(self):
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
