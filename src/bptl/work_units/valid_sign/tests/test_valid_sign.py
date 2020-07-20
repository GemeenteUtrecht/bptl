import json
import re
import uuid

from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.tasks.models import TaskMapping
from bptl.work_units.valid_sign.tasks import (
    CreateValidSignPackageTask,
    ValidSignReminderTask,
)
from bptl.work_units.valid_sign.tests.utils import mock_service_oas_get
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory

VALIDSIGN_URL = "https://try.validsign.test.nl/"
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
    "inhoud": CONTENT_1,
    "titel": "Test Doc 1",
}

RESPONSE_2 = {
    "url": DOCUMENT_2,
    "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
    "inhoud": CONTENT_2,
    "titel": "Test Doc 2",
}

SIGNER_1 = {
    "email": "test.signer1@example.com",
    "firstName": "Test name 1",
    "lastName": "Test surname 1",
}


SIGNER_2 = {
    "email": "test.signer2@example.com",
    "firstName": "Test name 2",
    "lastName": "Test surname 2",
}

FORMATTED_SIGNER_1 = {
    "id": "b787a5c8-0d43-4fcc-9163-f9ee800598bb",
    "type": "SIGNER",
    "signers": [SIGNER_1],
}

FORMATTED_SIGNER_2 = {
    "id": "dd6dd079-0909-4ca5-bf28-47e7fc959c96",
    "type": "SIGNER",
    "signers": [SIGNER_2],
}

OWNER = {
    "type": "OWNER",
    "signers": [
        {
            "email": "test.owner@example.com",
            "firstName": "Test name owner",
            "lastName": "Test surname owner",
        }
    ],
}


def mock_roles_get(m, package):
    m.get(
        f"{VALIDSIGN_URL}api/packages/{package['id']}/roles",
        json={"count": 3, "results": [OWNER, FORMATTED_SIGNER_1, FORMATTED_SIGNER_2]},
    )


def mock_create_approval_post(m, package):
    url = f"{VALIDSIGN_URL}api/packages/{package['id']}/documents/(?:.*)/approvals"
    matcher = re.compile(url)
    m.post(matcher,)


@requests_mock.Mocker()
class ValidSignTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="CreateValidSignPackage",
            callback="bptl.work_units.valid_sign.tasks.CreateValidSignPackage",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=ZRC_URL,
            service__api_type="zrc",
            alias="DocumentenAPI",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=VALIDSIGN_URL,
            service__api_type="orc",
            alias="ValidSignAPI",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="CreateValidSignPackage",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "documents": {"type": "List", "value": [DOCUMENT_1, DOCUMENT_2]},
                "signers": {"type": "List", "value": [SIGNER_1, SIGNER_2]},
                "packageName": {"type": "String", "value": "Test package name"},
            },
        )

    def test_format_signers(self, m):
        mock_service_oas_get(
            m=m, url=VALIDSIGN_URL, service="validsign", extension="yaml"
        )

        task = CreateValidSignPackageTask(self.fetched_task)

        formatted_signer = task.format_signers([SIGNER_1])
        self.assertEqual(formatted_signer, [{"type": "SIGNER", "signers": [SIGNER_1]}])

        formatted_signers = task.format_signers([SIGNER_1, SIGNER_2])
        self.assertEqual(
            formatted_signers,
            [
                {"type": "SIGNER", "signers": [SIGNER_1]},
                {"type": "SIGNER", "signers": [SIGNER_2]},
            ],
        )

    def test_get_documents_from_api(self, m):
        mock_service_oas_get(m=m, url=ZRC_URL, service="documenten", extension="json")

        # Mock call to retrieve the documents from the API
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(DOCUMENT_2, json=RESPONSE_2)
        # Mock calls to retrieve the content of the documents
        m.get(CONTENT_1, content=b"Test content 1")
        m.get(CONTENT_2, content=b"Test content 2")

        task = CreateValidSignPackageTask(self.fetched_task)
        documents = task._get_documents_from_api()

        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0], (RESPONSE_1["titel"], b"Test content 1"))
        self.assertEqual(documents[1], (RESPONSE_2["titel"], b"Test content 2"))

    def test_create_package(self, m):
        mock_service_oas_get(
            m=m, url=VALIDSIGN_URL, service="validsign", extension="yaml"
        )

        test_package_id = "BW5fsOKyhj48A-fRwjPyYmZ8Mno="
        path = "api/packages"
        m.post(
            f"{VALIDSIGN_URL}{path}", json={"id": test_package_id},
        )

        task = CreateValidSignPackageTask(self.fetched_task)
        package = task.create_package()

        self.assertEqual(package["id"], test_package_id)

        for request_body in m.request_history:
            if request_body.path.lstrip("/") != path:
                continue
            body = json.loads(request_body.text)
            self.assertEqual(body["name"], "Test package name")
            self.assertEqual(body["type"], "PACKAGE")
            expected_roles = [
                {"type": "SIGNER", "signers": [SIGNER_1]},
                {"type": "SIGNER", "signers": [SIGNER_2]},
            ]
            self.assertEqual(body["roles"], expected_roles)

    def test_add_documents_and_signers_to_package(self, m):
        mock_service_oas_get(
            m=m, url=VALIDSIGN_URL, service="validsign", extension="yaml"
        )
        mock_service_oas_get(m=m, url=ZRC_URL, service="documenten", extension="json")

        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}

        # Two test documents are added to the package
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(CONTENT_1, content=b"Test content 1")
        m.get(DOCUMENT_2, json=RESPONSE_2)
        m.get(CONTENT_2, content=b"Test content 2")

        # The task will retrieve the roles from ValidSign, so mock the call
        mock_roles_get(m, test_package)

        test_document_response = {
            "id": "75204439c02fffeddaeb224a1ded0ea07016456c9069eadd",
            "name": "Test Document",
        }

        m.post(
            f"{VALIDSIGN_URL}api/packages/{test_package['id']}/documents",
            json=test_document_response,
        )

        task = CreateValidSignPackageTask(self.fetched_task)
        document_list = task.add_documents_and_approvals_to_package(test_package)

        # Since there are two documents in the package, the document list should contain 2 docs
        self.assertEqual(
            document_list, [test_document_response, test_document_response]
        )

        # Check that the request headers and body for POSTing the documents were formatted correctly
        for mocked_request in m.request_history[-2:]:
            self.assertEqual(mocked_request._request.headers["Accept"], "*/*")
            self.assertIn(
                "multipart/form-data; boundary=",
                mocked_request._request.headers["Content-Type"],
            )
            body = mocked_request._request.body.decode()
            self.assertIn('Content-Disposition: form-data; name="payload"', body)
            self.assertIn(
                'Content-Disposition: form-data; name="file"; filename="file"', body
            )

    def test_get_signers(self, m):
        mock_service_oas_get(
            m=m, url=VALIDSIGN_URL, service="validsign", extension="yaml"
        )
        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}

        # The task will retrieve the roles from ValidSign, so mock the call
        mock_roles_get(m, test_package)

        task = CreateValidSignPackageTask(self.fetched_task)
        signers = task._get_signers_from_package(test_package)

        # Test that the signers are returned and not the package owner
        self.assertEqual(len(signers), 2)
        self.assertEqual(signers[0], FORMATTED_SIGNER_1)
        self.assertEqual(signers[1], FORMATTED_SIGNER_2)


@requests_mock.Mocker()
class ValidSignReminderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="ValidSignReminder",
            callback="bptl.work_units.valid_sign.tasks.CreateValidSignPackage",
        )

        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=VALIDSIGN_URL,
            service__api_type="orc",
            alias="ValidSignAPI",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="ValidSignReminder",
            worker_id="reminder-worker-id",
            task_id="reminder-task-id",
            variables={
                "packageId": {
                    "type": "String",
                    "value": "BW5fsOKyhj48A-fRwjPyYmZ8Mno=",
                },
                "email": {"type": "String", "value": "test@example.com"},
            },
        )

    def test_send_reminder(self, m):
        mock_service_oas_get(
            m=m, url=VALIDSIGN_URL, service="validsign", extension="yaml"
        )
        path = "api/packages/BW5fsOKyhj48A-fRwjPyYmZ8Mno=/notifications"
        m.post(f"{VALIDSIGN_URL}{path}")

        task = ValidSignReminderTask(self.fetched_task)
        task.perform()

        for request_body in m.request_history:
            if request_body.path.lstrip("/") != path:
                continue
            body = json.loads(request_body.text)
            self.assertEqual({"email": "test@example.com"}, body)
