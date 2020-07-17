import io
import json
import logging
from typing import List, Tuple

import requests
from zgw_consumers.client import ZGWClient

from bptl.tasks.base import WorkUnit, check_variable
from bptl.tasks.models import TaskMapping
from bptl.tasks.registry import register

logger = logging.getLogger(__name__)


class ValidSignTask(WorkUnit):

    _validsign_client = None

    def get_validsign_client(self, topic_name: str) -> ZGWClient:
        if self._validsign_client is None:
            default_services = TaskMapping.objects.get(
                topic_name=topic_name
            ).defaultservice_set.select_related("service")
            services_by_alias = {svc.alias: svc.service for svc in default_services}

            alias = "ValidSignAPI"
            if alias not in services_by_alias:
                raise RuntimeError(f"Service alias '{alias}' not found.")

            self._validsign_client = services_by_alias[alias].build_client()
        return self._validsign_client

    def perform(self) -> dict:
        raise NotImplementedError


@register
class CreateValidSignPackageTask(ValidSignTask):
    """Create a ValidSign package with signers and documents and send a signing request to the signers.

    **Required process variables**

    * ``documents``: List of strings. List of API URLs where the documents to be signed can be retrieved.
        The API must comply with the Documenten API 1.0.x (https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/index).

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

    **Sets the process variables**

    * ``packageId``: string. ID of the ValidSign package created by the task.
    """

    _documents_client = None

    def get_documents_client(self, topic_name: str) -> ZGWClient:
        if self._documents_client is None:
            default_services = TaskMapping.objects.get(
                topic_name=topic_name
            ).defaultservice_set.select_related("service")
            services_by_alias = {svc.alias: svc.service for svc in default_services}

            alias = "DocumentenAPI"
            if alias not in services_by_alias:
                raise RuntimeError(f"Service alias '{alias}' not found.")

            self._documents_client = services_by_alias[alias].build_client()
        return self._documents_client

    def format_signers(self, signers: List[dict]) -> List[dict]:
        """Format the signer information into an array of JSON objects as needed by ValidSign."""

        return [{"type": "SIGNER", "signers": [signer]} for signer in signers]

    def _get_documents_from_api(self) -> List[Tuple[str, bytes]]:
        """Retrieve the documents and their content from the Documenten API."""

        logger.debug("Retrieving documents from Documenten API")

        variables = self.task.get_variables()
        document_urls = check_variable(variables, "documents")
        document_client = self.get_documents_client(topic_name="CreateValidSignPackage")

        documents = []
        for document_url in document_urls:
            # Retrieving the document
            document_data = document_client.retrieve(
                resource="enkelvoudiginformatieobject", url=document_url,
            )

            # Retrieving the content of the document
            # Need use requests directly instead of `document_client.request()` since the response is not in JSON format
            response = requests.get(
                document_data["inhoud"], headers=document_client.auth.credentials(),
            )

            documents.append((document_data["titel"], io.BytesIO(response.content)))

        return documents

    def _get_signers_from_package(self, package: dict) -> List[dict]:
        """Retrieve all the roles from a ValidSign package and return those that are signers."""

        logger.debug("Retrieving the roles from validSign package '%s'", package["id"])

        response = self.get_validsign_client(
            topic_name="CreateValidSignPackage"
        ).request(
            path=f"api/packages/{package['id']}/roles",
            operation="api.packages._packageId.roles.get",
            method="GET",
        )

        roles = response["results"]
        # Not all the roles are signers (one of them is the account owner)
        return [role for role in roles if role["type"] == "SIGNER"]

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

        package = self.get_validsign_client(
            topic_name="CreateValidSignPackage"
        ).request(
            path="api/packages", operation="api.packages.post", method="POST", json=body
        )

        return package

    def add_documents_to_package(self, package: dict) -> List[dict]:
        """Add documents to the package."""

        logger.debug("Adding documents to ValidSign package '%s'", package["id"])

        documents = self._get_documents_from_api()

        # Multiple files can be added in one request by passing the following 'files' parameter
        # to the request, but then not sure how to specify the filename yet...
        # files = [("files[]", content) for name, content in documents]

        validsign_client = self.get_validsign_client(
            topic_name="CreateValidSignPackage"
        )

        attached_documents = []
        for doc_name, doc_content in documents:
            url = f"{validsign_client.base_url}/api/packages/{package['id']}/documents"
            payload = {"name": doc_name}
            body = {"payload": json.dumps(payload)}
            file = [("file", doc_content)]

            # Not using validsign_client because the request doesn't get formatted properly
            response = requests.post(
                url=url, headers=validsign_client.auth_header, data=body, files=file
            )
            response.raise_for_status()
            attached_doc = response.json()

            attached_documents.append(attached_doc)

        return attached_documents

    def create_approval_for_documents(self, package: dict, documents: List[dict]):
        """Create an approval in the specified documents for all signers.

        The approval is a placeholder for where a signature will go. According to
        https://apidocs.validsign.nl/validsign_integrator_guide.pdf the anchor extraction cannot be used
        with the API call to create an approval. So, the position has to be provided. If no ``top``, ``left``,
        ``width`` and ``height`` are given, then an 'acceptance button' appears under the document.
        """

        logger.debug(
            "Creating approvals for documents in ValidSign package '%s'", package["id"]
        )

        signers = self._get_signers_from_package(package)

        # Settings for the size and the place of the signature field in the document
        signature_width = 150
        signature_height = 50
        left_offset = 0

        validsign_client = self.get_validsign_client(
            topic_name="CreateValidSignPackage"
        )

        # For all the documents, create an approval for each signer
        for document in documents:
            approval_path = (
                f"api/packages/{package['id']}/documents/{document['id']}/approvals"
            )
            # FIXME the signatures are stacked vertically, but if they reach the end of the page it causes a 500 error
            for counter, signer in enumerate(signers):
                approval_settings = [
                    {
                        "top": counter * signature_height,
                        "left": left_offset,
                        "width": signature_width,
                        "height": signature_height,
                        "page": 0,
                        "type": "SIGNATURE",
                        "subtype": "FULLNAME",
                    }
                ]
                data = {"role": f"{signer['id']}", "fields": approval_settings}
                validsign_client.request(
                    path=approval_path,
                    operation="api.packages._packageId.documents._documentId.approvals.post",
                    method="POST",
                    json=data,
                )

    def send_package(self, package: dict):
        """Change the status of the package to 'SENT'

        When the status of the package is changed, an email is automatically sent to all the signers with a
        link where they can sign the documents.
        """

        logger.debug("Setting the status of package '%s' to SENT", package["id"])
        body = {"status": "SENT"}

        self.get_validsign_client("CreateValidSignPackage").request(
            path=f"api/packages/{package['id']}",
            operation="api.packages._packageId.post",
            method="PUT",
            json=body,
        )

    def perform(self) -> dict:

        package = self.create_package()
        documents = self.add_documents_to_package(package)
        self.create_approval_for_documents(package, documents)
        self.send_package(package)

        return {"packageId": package["id"]}


@register
class ValidSignReminderTask(ValidSignTask):
    """Email a reminder (with links) to signers that they need to sign documents through ValidSign.

    **Required process variables**

    * ``packageId``: string with the ValidSign Id of a package
    * ``email``: the email address of the signer who needs a reminder

    **Sets no process variables**

    """

    def send_reminder(self, package_id: str, email: str):
        logger.debug("Sending a reminder to '%s' through ValidSign", email)

        body = {"email": email}
        self.get_validsign_client("ValidSignReminder").request(
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
