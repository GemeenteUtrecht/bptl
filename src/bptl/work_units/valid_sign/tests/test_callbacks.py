"""
Test the callback machinery from ValidSign.

Example callback:

.. code-block:: http

    POST https://webhook.site/b62b7cc0-4da5-4b0f-bbd5-880769f44d47 HTTP/1.1
    Host: webhook.site
    Accept-Encoding: gzip,deflate
    User-Agent:
    Authorization: Basic test-callback-key
    Content-Type: application/json; charset=utf-8

    {
      "@class": "com.silanis.esl.packages.event.ESLProcessEvent",
      "name": "PACKAGE_COMPLETE",
      "sessionUser": "30ba8506-9819-46aa-a22d-c0114ba34cd0",
      "packageId": "LWsUTvGgE4WpOvaQPT16idnxNj8=",
      "message": null,
      "documentId": null,
      "createdDate": "2020-08-21T14:12:34.544Z"
    }
"""

from django.urls import reverse_lazy

from rest_framework import status
from rest_framework.test import APITestCase

from ..models import ValidSignConfiguration

BODY = {
    "@class": "com.silanis.esl.packages.event.ESLProcessEvent",
    "name": "PACKAGE_COMPLETE",
    "sessionUser": "30ba8506-9819-46aa-a22d-c0114ba34cd0",
    "packageId": "LWsUTvGgE4WpOvaQPT16idnxNj8=",
    "message": None,
    "documentId": None,
    "createdDate": "2020-08-21T14:12:34.544Z",
}


class CallbackTests(APITestCase):

    endpoint = reverse_lazy("valid_sign:callbacks")

    def test_no_auth_perm_denied(self):
        response = self.client.post(self.endpoint, BODY)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_header_pattern(self):
        values = ["Token foo", "Basic foo bar baz", "some-key", "Basic"]
        for value in values:
            with self.subTest(header_value=value):
                response = self.client.post(
                    self.endpoint, BODY, HTTP_AUTHORIZATION=value
                )

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_basic_auth_key(self):
        response = self.client.post(
            self.endpoint, BODY, HTTP_AUTHORIZATION="Basic wrong-key"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_correct_basic_auth_key(self):
        config = ValidSignConfiguration.get_solo()

        response = self.client.post(
            self.endpoint, BODY, HTTP_AUTHORIZATION=f"Basic {config.auth_key}"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
