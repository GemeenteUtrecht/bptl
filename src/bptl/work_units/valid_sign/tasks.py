import json
import logging
from io import BytesIO
from typing import List, Tuple

from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.utils.crypto import get_random_string

import requests
from zgw_consumers.client import ZGWClient

from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.registry import register

from .client import DRCClientPool, get_client, require_validsign_service
from .models import CreatedPackage

logger = logging.getLogger(__name__)


class NoService(Exception):
    pass


class NoAuth(Exception):
    pass


class DoesNotExist(Exception):
    pass


class ValidSignTask(WorkUnit):
    @property
    def client(self) -> ZGWClient:
        if not hasattr(self, "_client"):
            self._client = get_client(self.task)
        return self._client


@register
@require_validsign_service
class CreateValidSignPackageTask(ValidSignTask):
    """Create a ValidSign package with signers and documents and send a signing request to the signers.

    **Required process variables**

    * ``documents``: List of strings. List of API URLs where the documents to be signed can be retrieved.
        The API must comply with the Documenten API 1.0.x (
        https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

    * ``signers``: JSON list with signers information. For ValidSign, the first name, the last name and the
        email address of each signer are required. Example ``signers``:

            .. code-block:: json

                [{
                    "email": "example.signer@example.com",
                    "firstName": "ExampleFirstName",
                    "lastName": "ExampleLastName"
                },
                {
                    "email": "another.signer@example.com",
                    "firstName": "AnotherFirstName",
                    "lastName": "AnotherLastName"
                }]

    * ``packageName``: string. Name of the ValidSign package that contains the documents to sign and the signers.
        This name appears in the notification-email that is sent to the signers.


    * ``services``: JSON Object of connection details for ZGW services:

        .. code-block:: json

          {
              "<drc alias1>": {"jwt": "Bearer <JWT value>"},
              "<drc alias2>": {"jwt": "Bearer <JWT value>"}
          }

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    * ``messageId``: string. The message ID to send back into the process when the
        package is signed by everyone. You can use this to continue process execution.
        If left empty, then no message will be sent.

    **Sets the process variables**

    * ``packageId``: string. ID of the ValidSign package created by the task.
    """

    def format_signers(self, signers: List[dict]) -> List[dict]:
        """Format the signer information into an array of JSON objects as needed by ValidSign."""

        return [{"type": "SIGNER", "signers": [signer]} for signer in signers]

    def _get_documents_from_api(self) -> List[Tuple[str, BytesIO]]:
        """Retrieve the documents and their content from the Documenten API."""

        logger.debug("Retrieving documents from Documenten API")

        variables = self.task.get_variables()
        document_urls = check_variable(variables, "documents")

        client_pool = DRCClientPool(variables)
        client_pool.populate_clients(self.task, document_urls)

        documents = []

        current_total_documents_size = 0
        for document_url in document_urls:
            # Getting the appropriate client
            document_client = client_pool.get_client_for(document_url)
            # Retrieving the document
            document_data = document_client.retrieve(
                resource="enkelvoudiginformatieobject",
                url=document_url,
            )

            # Retrieving the content of the document
            # Need use requests directly instead of `document_client.request()` since the response is not in JSON format
            response = requests.get(
                document_data["inhoud"],
                headers=document_client.auth_header,
                stream=True,
            )

            # Get the document size in bytes
            document_size = document_data["bestandsomvang"]

            # If the size of the document is above the max size or if all the documents together have already reached
            # the maximum size, write the file content to a temporary file
            if (
                document_size > settings.MAX_DOCUMENT_SIZE
                or (current_total_documents_size + document_size)
                > settings.MAX_TOTAL_DOCUMENT_SIZE
            ):
                # The file is created with rb+ mode by default
                tmp_file_object = TemporaryUploadedFile(
                    name=f"{document_data['titel']}-{get_random_string(length=5)}.tempfile",
                    content_type="application/octet-stream",
                    size=document_size,
                    charset=None,  # Required argument in TemporaryUploadedFile, but not in parent class UploadedFile
                )
                for chunk in response.iter_content(chunk_size=settings.CHUNK_SIZE):
                    tmp_file_object.write(chunk)
                tmp_file_object.flush()
                doc_tuple = (document_data["titel"], tmp_file_object)
            else:
                doc_tuple = (document_data["titel"], BytesIO(response.content))
                current_total_documents_size += document_size

            response.close()

            documents.append(doc_tuple)

        return documents

    def _get_signers_from_package(self, package: dict) -> List[dict]:
        """Retrieve all the roles from a ValidSign package and return those that are signers."""

        logger.debug("Retrieving the roles from validSign package '%s'", package["id"])

        response = self.client.request(
            path=f"api/packages/{package['id']}/roles",
            operation="api.packages._packageId.roles.get",
            method="GET",
        )

        roles = response["results"]
        # Not all the roles are signers (one of them is the account owner)
        return [role for role in roles if role["type"] == "SIGNER"]

    def _get_approvals(self, signers: List[dict]) -> List[dict]:
        """Make approvals from signers

        The approval is a placeholder for where a signature from a signer will go.
        """

        fields = [
            {
                "type": "SIGNATURE",
                "subtype": "FULLNAME",
                "extractAnchor": {
                    "anchorText": "Capture Signature",
                    "index": 0,
                    "characterIndex": 0,
                    "anchorPoint": "BOTTOMLEFT",
                    "leftOffset": 0,
                    "topOffset": 0,
                    "width": 150,
                    "height": 50,
                },
            }
        ]

        approvals = []
        for signer in signers:
            approvals.append({"role": f"{signer['id']}", "fields": fields})

        return approvals

    def create_package(self) -> dict:
        """Create a ValidSign package with the name specified by the process variable and add the signers to it."""

        logger.debug("Creating ValidSign package")

        variables = self.task.get_variables()
        signers = self.format_signers(check_variable(variables, "signers"))
        package_name = check_variable(variables, "packageName")

        body = {
            "name": package_name,
            "type": "PACKAGE",
            "roles": signers,
        }

        package = self.client.request(
            path="api/packages", operation="api.packages.post", method="POST", json=body
        )

        return package

    def add_documents_and_approvals_to_package(self, package: dict) -> List[dict]:
        """Add documents and approvals to the package."""

        logger.debug(
            "Adding documents and approvals to ValidSign package '%s'", package["id"]
        )

        documents = self._get_documents_from_api()

        # Multiple files can be added in one request by passing the following 'files' parameter
        # to the request, but then not sure how to specify the filename yet...
        # files = [("files[]", content) for name, content in documents]

        signers = self._get_signers_from_package(package)
        approvals = self._get_approvals(signers)

        attached_documents = []
        for doc_name, doc_content in documents:
            url = f"{self.client.base_url}api/packages/{package['id']}/documents"
            payload = {"name": doc_name, "extract": True, "approvals": approvals}
            body = {"payload": json.dumps(payload)}
            doc_content.seek(0)

            # if doc_content is a TemporaryUploadedFile, this does a streaming upload
            file = [("file", doc_content)]

            # Not using validsign_client because the request doesn't get formatted properly,
            # since this a multipart/form-data call while zds_client only supports JSON.
            response = requests.post(
                url=url, headers=self.client.auth_header, data=body, files=file
            )
            doc_content.close()

            response.raise_for_status()
            attached_doc = response.json()
            attached_documents.append(attached_doc)

        return attached_documents

    def send_package(self, package: dict):
        """Change the status of the package to 'SENT'

        When the status of the package is changed, an email is automatically sent to all the signers with a
        link where they can sign the documents.
        """

        logger.debug("Setting the status of package '%s' to SENT", package["id"])
        body = {"status": "SENT"}

        self.client.request(
            path=f"api/packages/{package['id']}",
            operation="api.packages._packageId.post",
            method="PUT",
            json=body,
        )

    def perform(self) -> dict:

        package = self.create_package()
        self.add_documents_and_approvals_to_package(package)
        self.send_package(package)

        CreatedPackage.objects.create(package_id=package["id"], task=self.task)

        return {"packageId": package["id"]}


@register
@require_validsign_service
class ValidSignReminderTask(ValidSignTask):
    """Email a reminder (with links) to signers that they need to sign documents through ValidSign.

    **Required process variables**

    * ``packageId``: string with the ValidSign Id of a package
    * ``email``: the email address of the signer who needs a reminder

    **Optional process variables**

    * ``bptlAppId``: the application ID of the app that caused this task to be executed.
      The app-specific credentials will be used for the API calls, if provided.

    **Sets no process variables**

    """

    def send_reminder(self, package_id: str, email: str):
        logger.debug("Sending a reminder to '%s' through ValidSign", email)

        body = {"email": email}
        self.client.request(
            path=f"api/packages/{package_id}/notifications",
            operation="api.packages._packageId.notifications.post",
            method="POST",
            json=body,
        )

    def perform(self) -> dict:

        variables = self.task.get_variables()

        package_id = check_variable(variables, "packageId")
        email = check_variable(variables, "email")

        self.send_reminder(package_id, email)

        return {}
