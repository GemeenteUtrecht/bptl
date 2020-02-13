from django.conf import settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase


class WorkUnitNotAuthTestCase(APITestCase):
    def test_post_workunit_notauth(self):
        data = {"topic": "zaak-initialize", "vars": {"someOtherVar": 123}}
        url = reverse("work-unit", args=(settings.REST_FRAMEWORK["DEFAULT_VERSION"],))

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
