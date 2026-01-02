from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from bptl.credentials.tests.factories import AppFactory, AppServiceCredentialsFactory
from bptl.tasks.models import BaseTask
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.tests.utils import paginated_response
from bptl.work_units.zgw.objects.client import (
    get_objects_client,
    get_objecttypes_client,
)

from .utils import OBJECTS_ROOT, OBJECTTYPES_ROOT


@requests_mock.Mocker()
class ObjectsandObjectTypesClientsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        objects = Service.objects.create(
            api_root=OBJECTS_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token ThisIsNotTheGreatestTokenInTheWorldThisIsJustATribute",
            label="Objects",
            slug="objects-client-test",
        )

        objecttypes = Service.objects.create(
            api_root=OBJECTTYPES_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token ThisIsNotTheGreatestTokenInTheWorldThisIsJustATributeType",
            label="ObjectTypes",
            slug="objecttypes-client-test",
        )
        task_mapping = TaskMappingFactory.create(topic_name="some-topic")
        DefaultServiceFactory.create(
            task_mapping=task_mapping,
            service=objects,
            alias="objects",
        )
        DefaultServiceFactory.create(
            task_mapping=task_mapping,
            service=objecttypes,
            alias="objecttypes",
        )
        app = AppFactory.create(app_id="some-app-id")
        AppServiceCredentialsFactory.create(
            app=app,
            service=objects,
            header_key="Other-Header",
            header_value="foobarbaz",
        )
        AppServiceCredentialsFactory.create(
            app=app,
            service=objecttypes,
            header_key="Other-Header",
            header_value="foobarbaz",
        )

    def test_objects_client(self, m):
        task = BaseTask.objects.create(
            topic_name="some-topic",
            variables={
                "bptlAppId": "some-app-id",
            },
        )

        client = get_objects_client(task)

        self.assertIsInstance(client.auth, dict)
        self.assertNotIn("Authorization", client.auth)
        self.assertEqual(
            client.auth["Other-Header"],
            "foobarbaz",
        )

        m.get(OBJECTS_ROOT, json={})

        client.get("")

        self.assertTrue("Other-Header" in m.request_history[0].headers)
        self.assertEqual(
            m.request_history[0].headers["Other-Header"],
            "foobarbaz",
        )

    def test_objecttypes_client(self, m):
        task = BaseTask.objects.create(
            topic_name="some-topic",
            variables={
                "bptlAppId": "some-app-id",
            },
        )

        client = get_objecttypes_client(task)

        self.assertIsInstance(client.auth, dict)
        self.assertNotIn("Authorization", client.auth)
        self.assertEqual(
            client.auth["Other-Header"],
            "foobarbaz",
        )

        m.get(OBJECTTYPES_ROOT, json={})

        client.get("")

        self.assertTrue("Other-Header" in m.request_history[0].headers)
        self.assertEqual(
            m.request_history[0].headers["Other-Header"],
            "foobarbaz",
        )
