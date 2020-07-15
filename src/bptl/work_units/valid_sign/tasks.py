import json
import logging
import uuid
from typing import List, Tuple

from django.conf import settings

import requests

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

logger = logging.getLogger(__name__)


@register
class ValidSignTask(WorkUnit):
    """
    Creates a ValidSign package with the name specified by the process variables and adds a set of documents and a set
    of signers. Once the package is ready, it sends an email to the signers to notify them that they need to sign the
    documents.

    **Required process variables**

    * ``documents``: List of strings. List of API URLs where the documents to be signed can be retrieved.
        The API is expected to return a JSON object with attributes ``titel`` (the document name) and ``inhoud`` (the
        URL where to retrieve the content).

    * ``signers``: List of dict. For ValidSign, the first name, the last name and the
        email address of each signer are required. Example ``signers``:

            .. code-block:: python

                [{
                    "email": "example.signer@example.com",
                    "firstName": "ExampleFirstName",
                    "lastName": "ExampleLastName",
                },
                {
                    "email": "another.signer@example.com",
                    "firstName": "AnotherFirstName",
                    "lastName": "AnotherLastName",
                }]

    * ``package_name``: string. Name of the ValidSign package that contains the documents to sign and the signers.
        This name appears in the notification-email that is sent to the signers.

    **Sets the process variables**

    * ``package_id``: string. ID of the ValidSign package created by the task.
    """

    _auth_header = {"Authorization": f"Basic {settings.VALIDSIGN_APIKEY}"}

    def format_signers(self, signers: List[dict]) -> List[dict]:
        """
        Formats the signer information into an array of JSON objects as needed by ValidSign.
        """
        formatted_signers = []

        for signer in signers:
            formatted_signers.append({"type": "SIGNER", "signers": [signer]})

        return formatted_signers

    def _get_documents_from_api(self) -> List[Tuple[str, bytes]]:
        """
        Retrieves the documents from Documenten API and returns a list of tuples with the name and the binary content
        of each document.
        """
        logger.debug("Retrieving documents from Documenten API")

        variables = self.task.get_variables()
        document_urls = variables.get("documents")

        documents = []
        for document_url in document_urls:
            # Retrieving the document
            response = requests.get(
                document_url,
                auth=(settings.DOCUMENT_API_USER, settings.DOCUMENT_API_PASSWORD),
            )
            response.raise_for_status()

            document_data = response.json()
            # Retrieving the content of the document
            response = requests.get(
                document_data.get("inhoud"),
                auth=(settings.DOCUMENT_API_USER, settings.DOCUMENT_API_PASSWORD),
            )
            response.raise_for_status()

            documents.append((document_data.get("titel"), response.content))

        return documents

    def _get_signers_from_package(self, package: dict) -> List[dict]:
        """
        Retrieves all the roles from a ValidSign package and returns all the signers.
        """
        logger.debug(
            f"Retrieving the roles from validSign package '{package.get('id')}'"
        )

        roles_url = (
            f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/roles"
        )
        response = requests.get(roles_url, headers=self._auth_header)
        response.raise_for_status()
        roles = response.json().get("results")
        # Not all the roles are signers (one of them is the account owner)
        return [role for role in roles if role.get("type") == "SIGNER"]

    def create_package(self) -> dict:
        """
        Creates a ValidSign package with the name specified by the process variables and adds the signers to it.
        """
        logger.debug("Creating ValidSign package")

        variables = self.task.get_variables()
        signers = self.format_signers(variables.get("signers"))
        package_name = variables.get("package_name")

        url = f"{settings.VALIDSIGN_ROOT_URL}api/packages"

        body = {
            "name": package_name,
            "type": "PACKAGE",
            "roles": signers,
        }

        response = requests.post(url, headers=self._auth_header, data=json.dumps(body))
        response.raise_for_status()
        package = response.json()

        return package

    def add_documents_to_package(self, package: dict) -> List[dict]:
        """
        Adds documents to the specified package and returns a list with the information about each document returned by
        ValidSign.
        """

        logger.debug(f"Adding documents to ValidSign package '{package.get('id')}'")

        documents = self._get_documents_from_api()

        post_url = (
            f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/documents"
        )

        # Multiple files can be added in one request by passing the following 'files' parameter
        # to the request, but then not sure how to specify the filename yet...
        # files = [("files[]", content) for name, content in documents]

        attached_documents = []
        for doc_name, doc_content in documents:
            payload = {"payload": f'{{"name": "{doc_name}"}}'}
            file = [("file", doc_content)]
            response = requests.post(
                post_url, headers=self._auth_header, files=file, data=payload
            )
            response.raise_for_status()
            attached_documents.append(response.json())

        return attached_documents

    def create_approval_for_documents(self, package: dict, documents: List[dict]):
        """
        Creates an approval (a placeholder for where a signature will go) in the
        specified documents for all signers.

        According to https://apidocs.validsign.nl/validsign_integrator_guide.pdf the anchor extraction cannot be used
        with the API call to create an approval. So, the position has to be provided. If no ``top``, ``left``,
        ``width`` and ``height`` are given, then an 'acceptance button' appears under the document.
        """

        logger.debug(
            f"Creating approvals for documents in ValidSign package '{package.get('id')}'"
        )

        signers = self._get_signers_from_package(package)

        # Settings for the size and the place of the signature field in the document
        signature_width = 150
        signature_height = 50
        left_offset = 0

        # For all the documents, create an approval for each signer
        for document in documents:
            approval_url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/documents/{document.get('id')}/approvals"
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
                data = {"role": f"{signer.get('id')}", "fields": approval_settings}
                response = requests.post(
                    approval_url, data=json.dumps(data), headers=self._auth_header
                )
                response.raise_for_status()

    def send_package(self, package: dict):
        """
        Changes the status of a package to "SENT". This automatically sends an email to all the signers with a
        link where they can sign the documents.
        """
        logger.debug(f"Setting the status of package '{package.get('id')}' to SENT")
        url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}"
        body = {"status": "SENT"}
        response = requests.put(url, headers=self._auth_header, data=json.dumps(body))
        response.raise_for_status()

    def perform(self) -> dict:
        package = self.create_package()
        documents = self.add_documents_to_package(package)
        self.create_approval_for_documents(package, documents)
        self.send_package(package)

        return {"package_id": package.get("id")}


class ValidSignReminderTask(WorkUnit):
    """
    Takes a ValidSign package ID and the email address of a signer and sends an email-reminder to the signer providing a
    link to where the documents can be signed.

    **Required process variables**

    * ``package_id``: string with the ValidSign Id of a package
    * ``email``: the email address of the signer who needs a reminder

    **Sets no process variables**

    """

    _auth_header = {"Authorization": f"Basic {settings.VALIDSIGN_APIKEY}"}

    def send_reminder(self, package_id: str, email: str):
        logger.debug(f"Sending a reminder to '{email}' through ValidSign")

        url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package_id}/notifications"
        body = {"email": email}
        response = requests.post(url, headers=self._auth_header, data=json.dumps(body))
        response.raise_for_status()

    def perform(self) -> dict:

        variables = self.task.get_variables()

        package_id = variables.get("package_id")
        email = variables.get("email")

        self.send_reminder(package_id, email)

        return {}
