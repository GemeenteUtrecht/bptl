from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.camunda.models import ExternalTask
from bptl.credentials.tests.factories import AppServiceCredentialsFactory
from bptl.tasks.models import TaskMapping
from bptl.tasks.tests.factories import DefaultServiceFactory

from ..tasks import start_xential_template

XENTIAL_API_ROOT = "https://alfresco.utrechtproeftuin.nl/alfresco/s/"
TEMPLATE_URL = "https://xential.nl/xential?resumeApplication=ID&loginTicketUuid=Uuid&afterBuildAction=close"


@requests_mock.Mocker()
class XentialTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        mapping = TaskMapping.objects.create(
            topic_name="xential-topic",
        )

        xential = Service.objects.create(
            label="xential",
            api_type=APITypes.orc,
            api_root=XENTIAL_API_ROOT,
            auth_type=AuthTypes.api_key,
            oas="",
        )

        DefaultServiceFactory.create(
            task_mapping=mapping,
            service=xential,
            alias="xential",
        )
        AppServiceCredentialsFactory.create(
            app__app_id="some-app-id",
            service=xential,
            header_key="Authorization",
            header_value="Basic ZGVtbzpkZW1v",
        )

    def test_start_template(self, m):
        m.get(
            f"{XENTIAL_API_ROOT}xential/templates",
            json={
                "data": {
                    "templates": [
                        {"templateName": "Interactief", "templateUuid": "1234567890"},
                        {"templateName": "Silent", "templateUuid": "0987654321"},
                    ],
                    "params": {"sessionId": "12345678901234", "uuid": "09876543211234"},
                }
            },
        )
        m.post(
            f"{XENTIAL_API_ROOT}xential/templates/start?nodeRef=some/node/ref",
            json={
                "xentialTemplateUrl": TEMPLATE_URL,
                "nodeRefParentFolder": "123456789098765",
            },
        )

        external_task = ExternalTask.objects.create(
            topic_name="xential-topic",
            worker_id="test-worker-id",
            task_id="test-task-id",
            variables={
                "bptlAppId": serialize_variable("some-app-id"),
                "nodeRef": serialize_variable("some/node/ref"),
                "templateUuid": serialize_variable(
                    "540d57cb-c7f2-4423-821e-fc17c857a404"
                ),
                "filename": serialize_variable("some-file-name"),
                "templateVariables": serialize_variable(
                    {"variable1": "String", "variable2": "String"}
                ),
            },
        )

        result = start_xential_template(external_task)

        self.assertEqual(result, {"buildId": None, "xentialTemplateUrl": TEMPLATE_URL})
