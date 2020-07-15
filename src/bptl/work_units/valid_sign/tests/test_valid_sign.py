import re

from django.conf import settings
from django.test import TestCase

import requests_mock

from bptl.camunda.models import ExternalTask
from bptl.work_units.valid_sign.tasks import ValidSignReminderTask, ValidSignTask

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

SIGNER_1 = {
    "id": "test-signer-1-id",
    "company": "Test Company",
    "email": "test.signer1@example.com",
    "firstName": "Test name 1",
    "lastName": "Test surname 1",
}


SIGNER_2 = {
    "id": "test-signer-2-id",
    "company": "Test Company",
    "email": "test.signer2@example.com",
    "firstName": "Test name 2",
    "lastName": "Test surname 2",
}

FORMATTED_SIGNER_1 = {
    "id": "test-signer-1-id",
    "name": "Test Signer 1",
    "type": "SIGNER",
    "index": 2,
    "signers": [SIGNER_1],
}

FORMATTED_SIGNER_2 = {
    "id": "test-signer-2-id",
    "name": "Test Signer 2",
    "type": "SIGNER",
    "index": 2,
    "signers": [SIGNER_2],
}

OWNER = {
    "id": "owner-id",
    "name": "Test Owner",
    "type": "OWNER",
    "index": 0,
    "signers": [
        {
            "id": "owner-id",
            "company": "Test Company",
            "email": "test.owner@example.com",
            "firstName": "Test name owner",
            "lastName": "Test surname owner",
            "phone": "000000000000",
            "title": "Developer",
        }
    ],
}


def mock_roles_get(m, package):
    m.get(
        f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/roles",
        json={"count": 3, "results": [OWNER, FORMATTED_SIGNER_1, FORMATTED_SIGNER_2]},
    )


def mock_create_approval_post(m, package):
    url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/documents/(?:.*)/approvals"
    matcher = re.compile(url)
    m.post(matcher,)


@requests_mock.Mocker()
class ValidSignTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="validsign",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "documents": {"type": "List", "value": [DOCUMENT_1, DOCUMENT_2]},
                "signers": {"type": "List", "value": [SIGNER_1, SIGNER_2]},
                "package_name": {"type": "String", "value": "Test package name"},
            },
        )

    def test_format_signers(self, m):
        task = ValidSignTask(self.fetched_task)

        formatted_signer_1 = task.format_signers([SIGNER_1])
        self.assertEqual(
            formatted_signer_1, [{"type": "SIGNER", "signers": [SIGNER_1]}]
        )

        formatted_signers = task.format_signers([SIGNER_1, SIGNER_2])
        self.assertEqual(
            formatted_signers,
            [
                {"type": "SIGNER", "signers": [SIGNER_1]},
                {"type": "SIGNER", "signers": [SIGNER_2]},
            ],
        )

    def test_get_documents_from_api(self, m):
        # Mock call to retrieve the documents from the API
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(DOCUMENT_2, json=RESPONSE_2)
        # Mock calls to retrieve the content of the documents
        m.get(CONTENT_1, content=b"Test content 1")
        m.get(CONTENT_2, content=b"Test content 2")

        task = ValidSignTask(self.fetched_task)
        documents = task._get_documents_from_api()

        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0], (RESPONSE_1["titel"], b"Test content 1"))
        self.assertEqual(documents[1], (RESPONSE_2["titel"], b"Test content 2"))

    def test_create_package(self, m):
        test_package_id = "BW5fsOKyhj48A-fRwjPyYmZ8Mno="
        m.post(
            f"{settings.VALIDSIGN_ROOT_URL}api/packages", json={"id": test_package_id},
        )

        task = ValidSignTask(self.fetched_task)
        package = task.create_package()

        self.assertEqual(package["id"], test_package_id)

    def test_add_documents_to_package(self, m):
        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}

        # Two test documents are added to the package
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(CONTENT_1, content=b"Test content 1")
        m.get(DOCUMENT_2, json=RESPONSE_2)
        m.get(CONTENT_2, content=b"Test content 2")

        test_document_response = {
            "id": "75204439c02fffeddaeb224a1ded0ea07016456c9069eadd",
            "name": "Test Document",
        }

        m.post(
            f"{settings.VALIDSIGN_ROOT_URL}api/packages/{test_package.get('id')}/documents",
            json=test_document_response,
        )

        task = ValidSignTask(self.fetched_task)
        document_list = task.add_documents_to_package(test_package)

        # Since there are two documents in the package, the document list should contain 2 docs
        self.assertEqual(
            document_list, [test_document_response, test_document_response]
        )

    def test_get_signers(self, m):
        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}

        # The task will retrieve the roles from ValidSign, so mock the call
        mock_roles_get(m, test_package)

        task = ValidSignTask(self.fetched_task)
        signers = task._get_signers_from_package(test_package)

        # Test that the signers are returned and not the package owner
        self.assertEqual(signers[0]["id"], FORMATTED_SIGNER_1["id"])
        self.assertEqual(signers[1]["id"], FORMATTED_SIGNER_2["id"])
        self.assertEqual(len(signers), 2)

    def test_create_approval(self, m):
        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}
        test_documents = [
            {
                "id": "75204439c02fffeddaeb224a1ded0ea07016456c9069eadd",
                "name": "Test Document 1",
            },
            {
                "id": "24a1ded0ea07016456c9069eadd75204439c02fffeddaeb2",
                "name": "Test Document 2",
            },
        ]

        mock_create_approval_post(m, test_package)
        mock_roles_get(m, test_package)

        task = ValidSignTask(self.fetched_task)
        task.create_approval_for_documents(test_package, test_documents)

        # One call to get the roles and 2 calls per document (to add the 2 signers) and there are 2 documents in total.
        self.assertEqual(m.call_count, 5)


@requests_mock.Mocker()
class ValidSignReminderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="validsign",
            worker_id="reminder-worker-id",
            task_id="reminder-task-id",
            variables={
                "package_id": {
                    "type": "String",
                    "value": "BW5fsOKyhj48A-fRwjPyYmZ8Mno=",
                },
                "email": {"type": "String", "value": "test@example.com"},
            },
        )

    def test_send_reminder(self, m):
        m.post(
            f"{settings.VALIDSIGN_ROOT_URL}api/packages/BW5fsOKyhj48A-fRwjPyYmZ8Mno=/notifications"
        )

        task = ValidSignReminderTask(self.fetched_task)
        task.perform()

        self.assertEqual(m.call_count, 1)
        request_body = m.request_history[0].text

        self.assertEqual('{"email": "test@example.com"}', request_body)
