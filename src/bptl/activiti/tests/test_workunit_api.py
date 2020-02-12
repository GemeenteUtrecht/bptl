from django.conf import settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from ..models import ServiceTask


class WorkUnitTestCase(APITestCase):
    def test_delete_besluit_cascades_properly(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        data = {"topic": "zaak-initialize", "vars": {"someOtherVar": 123}}
        url = reverse("work-unit", args=(settings.REST_FRAMEWORK["DEFAULT_VERSION"],))
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        service_task = ServiceTask.objects.get()

        self.assertEqual(service_task.topic_name, "zaak-initialize")
