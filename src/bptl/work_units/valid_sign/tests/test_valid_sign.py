import json
import re

from django.core.files.uploadedfile import TemporaryUploadedFile
from django.test import TestCase, override_settings, tag

import jwt
import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes

from bptl.camunda.models import ExternalTask
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.models import TaskMapping
from bptl.work_units.zgw.tests.factories import DefaultServiceFactory
from bptl.work_units.zgw.tests.utils import mock_service_oas_get

from ..tasks import CreateValidSignPackageTask, ValidSignReminderTask, ValidSignTask
from .utils import VALIDSIGN_API_DOCS, mock_validsign_oas_get

VALIDSIGN_URL = "https://try.validsign.test.nl/"
DRC_URL = "https://some.drc.nl/api/v1/"
OTHER_DRC_URL = "https://other.drc.nl/api/v1/"

DOCUMENT_1 = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/4f8b4811-5d7e-4e9b-8201-b35f5101f891/"
)
DOCUMENT_2 = (
    f"{DRC_URL}enkelvoudiginformatieobjecten/b7218c76-7478-41e9-a088-54d2f914a713/"
)
DOCUMENT_3 = f"{OTHER_DRC_URL}enkelvoudiginformatieobjecten/c3714142-4d6b-450a-9e66-42cc2ef187be/"
CONTENT_URL_1 = f"{DOCUMENT_1}download/"
CONTENT_URL_2 = f"{DOCUMENT_2}download/"
CONTENT_URL_3 = f"{DOCUMENT_3}download/"
CONTENT_1 = b"Test content 1"
CONTENT_2 = b"Test content 2"
CONTENT_3 = b"Test content 3"

RESPONSE_1 = {
    "url": DOCUMENT_1,
    "uuid": "4f8b4811-5d7e-4e9b-8201-b35f5101f891",
    "inhoud": CONTENT_URL_1,
    "titel": "Test Doc 1",
    "bestandsomvang": 14,
}

RESPONSE_2 = {
    "url": DOCUMENT_2,
    "uuid": "b7218c76-7478-41e9-a088-54d2f914a713",
    "inhoud": CONTENT_URL_2,
    "titel": "Test Doc 2",
    "bestandsomvang": 14,
}

RESPONSE_3 = {
    "url": DOCUMENT_3,
    "uuid": "c3714142-4d6b-450a-9e66-42cc2ef187be",
    "inhoud": CONTENT_URL_3,
    "titel": "Test Doc 3",
    "bestandsomvang": 14,
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
    m.post(
        matcher,
    )


@requests_mock.Mocker()
class ValidSignTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="CreateValidSignPackage",
            callback="bptl.work_units.valid_sign.tasks.CreateValidSignPackage",
        )
        drc_svc = DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=DRC_URL,
            service__api_type="drc",
            alias="drc",
        )
        cls.drc = drc_svc.service
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=VALIDSIGN_URL,
            service__api_type="orc",
            service__oas=VALIDSIGN_API_DOCS,
            alias="ValidSignAPI",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="CreateValidSignPackage",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "documents": serialize_variable([DOCUMENT_1, DOCUMENT_2]),
                "signers": serialize_variable([SIGNER_1, SIGNER_2]),
                "packageName": serialize_variable("Test package name"),
                "services": serialize_variable({"drc": {"jwt": "Bearer 12345"}}),
            },
        )

    def test_format_signers(self, m):
        mock_validsign_oas_get(m)
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

    @tag("this")
    def test_get_documents_from_api(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")

        # Mock call to retrieve the documents from the API
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(DOCUMENT_2, json=RESPONSE_2)
        # Mock calls to retrieve the content of the documents
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(
            CONTENT_URL_2,
            content=CONTENT_2,
        )

        task = CreateValidSignPackageTask(self.fetched_task)
        documents = task._get_documents_from_api()

        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0][0], RESPONSE_1["titel"])
        self.assertEqual(documents[0][1].read(), CONTENT_1)
        self.assertEqual(documents[1][0], RESPONSE_2["titel"])
        self.assertEqual(documents[1][1].read(), CONTENT_2)

        self.assertEqual(m.request_history[-1].headers["Authorization"], "Bearer 12345")

    @tag("this")
    def test_get_documents_from_api_credentials_store(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")
        AppServiceCredentialsFactory.create(
            app__app_id="some-app",
            service=self.drc,
            client_id="foo",
            secret="bar",
        )

        # Mock call to retrieve the documents from the API
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(DOCUMENT_2, json=RESPONSE_2)
        # Mock calls to retrieve the content of the documents
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(
            CONTENT_URL_2,
            content=CONTENT_2,
        )

        task = CreateValidSignPackageTask(self.fetched_task)
        task._get_documents_from_api()

        token = m.request_history[-1].headers["Authorization"].split(" ")[1]
        claims = jwt.decode(token, key="bar", algorithms=["HS256"])

        self.assertEqual(claims["client_id"], "foo")

    @override_settings(MAX_DOCUMENT_SIZE=10)
    def test_get_large_documents_from_api(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")

        # Mock call to retrieve the documents from the API
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(DOCUMENT_2, json=RESPONSE_2)

        # Mock calls to retrieve the content of the documents
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(
            CONTENT_URL_2,
            content=CONTENT_2,
        )

        task = CreateValidSignPackageTask(self.fetched_task)
        documents = task._get_documents_from_api()

        for index, doc in enumerate(documents):
            self.assertTrue(isinstance(documents[index][1], TemporaryUploadedFile))
            documents[index][1].seek(0)
            uploaded_content = documents[index][1].read()

            self.assertEqual(
                uploaded_content, f"Test content {index+1}".encode("utf-8")
            )

    @override_settings(MAX_TOTAL_DOCUMENT_SIZE=20)
    def test_many_documents_from_api(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")

        # Mock call to retrieve the documents from the API
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(DOCUMENT_2, json=RESPONSE_2)

        # Mock calls to retrieve the content of the documents
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(
            CONTENT_URL_2,
            content=CONTENT_2,
        )

        task = CreateValidSignPackageTask(self.fetched_task)
        documents = task._get_documents_from_api()

        self.assertFalse(isinstance(documents[0][1], TemporaryUploadedFile))
        self.assertTrue(isinstance(documents[1][1], TemporaryUploadedFile))

    def test_create_package(self, m):
        mock_validsign_oas_get(m)

        test_package_id = "BW5fsOKyhj48A-fRwjPyYmZ8Mno="
        path = "api/packages"
        m.post(
            f"{VALIDSIGN_URL}{path}",
            json={"id": test_package_id},
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
        mock_validsign_oas_get(m)
        mock_service_oas_get(m, DRC_URL, "drc")

        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}

        # Two test documents are added to the package
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(DOCUMENT_2, json=RESPONSE_2)
        m.get(
            CONTENT_URL_2,
            content=CONTENT_2,
        )

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
        mock_validsign_oas_get(m)
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
class ValidSignMultipleDocsAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="CreateValidSignPackage",
            callback="bptl.work_units.valid_sign.tasks.CreateValidSignPackage",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=DRC_URL,
            service__api_type="drc",
            alias="drc1",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=OTHER_DRC_URL,
            service__api_type="drc",
            alias="drc2",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=VALIDSIGN_URL,
            service__api_type="orc",
            service__oas=VALIDSIGN_API_DOCS,
            alias="ValidSignAPI",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="CreateValidSignPackage",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "documents": serialize_variable([DOCUMENT_1, DOCUMENT_3]),
                "signers": serialize_variable([SIGNER_1, SIGNER_2]),
                "packageName": serialize_variable("Test package name"),
                "services": serialize_variable(
                    {
                        "drc1": {"jwt": "Bearer 12345"},
                        "drc2": {"jwt": "Bearer 789"},
                    }
                ),
            },
        )

    def test_get_documents_from_api(self, m):
        mock_service_oas_get(m, DRC_URL, "drc")
        mock_service_oas_get(m, OTHER_DRC_URL, "drc")
        # Mock call to retrieve the documents from the API
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(DOCUMENT_3, json=RESPONSE_3)
        # Mock calls to retrieve the content of the documents
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(
            CONTENT_URL_3,
            content=CONTENT_3,
        )

        task = CreateValidSignPackageTask(self.fetched_task)
        documents = task._get_documents_from_api()

        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0][0], RESPONSE_1["titel"])
        self.assertEqual(documents[0][1].read(), CONTENT_1)
        self.assertEqual(documents[1][0], RESPONSE_3["titel"])
        self.assertEqual(documents[1][1].read(), CONTENT_3)

    def test_add_documents_and_signers_to_package(self, m):
        mock_validsign_oas_get(m)
        mock_service_oas_get(m, DRC_URL, "drc")
        mock_service_oas_get(m, OTHER_DRC_URL, "drc")
        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}

        # Two test documents are added to the package
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(DOCUMENT_3, json=RESPONSE_3)
        m.get(
            CONTENT_URL_3,
            content=CONTENT_3,
        )

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

    @override_settings(MAX_DOCUMENT_SIZE=10)
    def test_add_large_documents_and_signers_to_package(self, m):
        mock_validsign_oas_get(m)
        mock_service_oas_get(m, DRC_URL, "drc")
        mock_service_oas_get(m, OTHER_DRC_URL, "drc")
        test_package = {"id": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="}

        # Two test documents are added to the package
        m.get(DOCUMENT_1, json=RESPONSE_1)
        m.get(
            CONTENT_URL_1,
            content=CONTENT_1,
        )
        m.get(DOCUMENT_3, json=RESPONSE_3)
        m.get(
            CONTENT_URL_3,
            content=CONTENT_3,
        )

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
                'Content-Disposition: form-data; name="file"; filename=', body
            )
            self.assertTrue("Test content ", body)


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
            service__oas=VALIDSIGN_API_DOCS,
            alias="ValidSignAPI",
        )

        cls.fetched_task = ExternalTask.objects.create(
            topic_name="ValidSignReminder",
            worker_id="reminder-worker-id",
            task_id="reminder-task-id",
            variables={
                "packageId": serialize_variable("BW5fsOKyhj48A-fRwjPyYmZ8Mno="),
                "email": serialize_variable("test@example.com"),
            },
        )

    def test_send_reminder(self, m):
        mock_validsign_oas_get(m)
        path = "api/packages/BW5fsOKyhj48A-fRwjPyYmZ8Mno=/notifications"
        m.post(f"{VALIDSIGN_URL}{path}")

        task = ValidSignReminderTask(self.fetched_task)
        task.perform()

        for request_body in m.request_history:
            if request_body.path.lstrip("/") != path:
                continue
            body = json.loads(request_body.text)
            self.assertEqual({"email": "test@example.com"}, body)


class CredentialsStoreAuthTests(TestCase):
    """
    Test the 1.0 credentials store functionality.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        default_service = DefaultServiceFactory.create(
            task_mapping__topic_name="some-topic",
            service__api_root=VALIDSIGN_URL,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.api_key,
            service__oas=VALIDSIGN_API_DOCS,
            service__header_key="default-header",
            service__header_value="bar",
            alias="ValidSignAPI",
        )
        AppServiceCredentialsFactory.create(
            app__app_id="some-app",
            service=default_service.service,
            header_key="custom-header",
            header_value="baz",
        )

    def test_base_service_auth(self):
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            variables={},
        )

        work_unit = ValidSignTask(fetched_task)

        self.assertEqual(
            work_unit.client.auth_header,
            {"default-header": "bar"},
        )

    def test_app_specific_service_auth(self):
        fetched_task = ExternalTask.objects.create(
            topic_name="some-topic",
            variables={
                "bptlAppId": serialize_variable("some-app"),
            },
        )

        work_unit = ValidSignTask(fetched_task)

        self.assertEqual(
            work_unit.client.auth_header,
            {"custom-header": "baz"},
        )
