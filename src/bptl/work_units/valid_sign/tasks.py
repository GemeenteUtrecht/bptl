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
    Takes a set of documents and a set of signers and uses the ValidSign signing
    process to make the signers digitally sign all the documents.

    **Required process variables**

    * ``documents``: list of API URLs where the documents to be signed can be retrieved.
        The API should provide the document name and the content.

    * ``signers``: array of signers. For ValidSign, the first name, the last name and the
        email address of each signer are required. Example ``signers``:

            .. code-block:: json

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

    **Sets the process variables**

    * ``signing_details``: List of JSON object with the urls at which the signers can go to sign the document, as well
        as the details of the signer. These include, among all the others that are provided by ValidSign, the email
        address, the first name and the last name of the signers. Example ``signing_details``:

            .. code-block:: json

                [
                    {
                        "url": "https://try.validsign.nl/signing_url_for_signer_1",
                        "roleId": "9b51bb7a-9934-4df5-bab8-a9856f3894f9",
                        "packageId": "7X2K7m-PXNKXnAGs0H3aLxWl8LA="
                        "signer_details": {
                            "type": "SIGNER",
                            "signers": [
                                {
                                    "email": "test.signer1@example.com",
                                    "firstName":"Test name 1",
                                    "lastName":"Test surname 1"
                                },
                            ]
                        }
                    },
                    {
                        "url": "https://try.validsign.nl/signing_url_for_signer_2",
                        "roleId": "0fcea629-de4a-47c1-96c1-4b78a5628dd9",
                        "packageId": "7X2K7m-PXNKXnAGs0H3aLxWl8LA="
                        "signer_details": {
                            "type": "SIGNER",
                            "signers": [
                                {
                                    "email": "test.signer2@example.com",
                                    "firstName":"Test name 2",
                                    "lastName":"Test surname 2"
                                },
                            ]
                        }
                    }
                ]

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
        Retrieves the documents from Documenten API and returns a list of the name and the binary content
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
            document_content = response.content

            documents.append((document_data.get("titel"), document_content))

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
        Creates a ValidSign package with the signers and the settings
        for the signing ceremony.
        """
        logger.debug("Creating ValidSign package")

        variables = self.task.get_variables()
        signers = self.format_signers(variables.get("signers"))

        url = f"{settings.VALIDSIGN_ROOT_URL}api/packages"

        body = {
            "name": f"Package {uuid.uuid1()}",
            "type": "PACKAGE",
            "description": "Package created by BPTL",
            "roles": signers,
        }

        response = requests.post(url, headers=self._auth_header, data=json.dumps(body))
        response.raise_for_status()
        package = response.json()

        return package

    def add_documents_to_package(self, package: dict) -> List[dict]:
        """
        Adds documents to the specified package and returns a list with the information about each document.
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
        with the API call to create an approval. So, the position has to be provided. If no ``top``, ``bottom``,
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
        Changes the status of a package to "SENT".
        """
        logger.debug(f"Setting the status of package '{package.get('id')}' to SENT")
        url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}"
        body = {"status": "SENT"}
        response = requests.put(url, headers=self._auth_header, data=json.dumps(body))
        response.raise_for_status()

    def get_signing_details(self, package: dict) -> List[dict]:
        """
        Retrieves all the urls where each signer can go to sign the documents. The signer details are returned along
        the signing ``url``, the ``roleId`` of the signer and the ``packageId`` of the package. Example
        of the returned object:

            .. code-block:: python

                [{
                    "url": "https://try.validsign.nl/signing_url_for_signer_1",
                    "roleId": "9b51bb7a-9934-4df5-bab8-a9856f3894f9",
                    "packageId": "7X2K7m-PXNKXnAGs0H3aLxWl8LA="
                    "signer_details": {
                        "type": "SIGNER",
                        "signers": [
                            {
                                "email": "test.signer1@example.com",
                                "firstName":"Test name 1",
                                "lastName":"Test surname 1"
                            },
                        ]
                    }
                },
                {
                    "url": "https://try.validsign.nl/signing_url_for_signer_2",
                    "roleId": "9b51bb7a-9934-4df5-bab8-a9856f3894f9",
                    "packageId": "BW5fsOKyhj48A-fRwjPyYmZ8Mno="
                    "signer_details": {
                        "type": "SIGNER",
                        "signers": [
                            {
                                "email": "test.signer2@example.com",
                                "firstName":"Test name 2",
                                "lastName":"Test surname 2"
                            },
                        ]
                    }
                }]

        For each signer, all the data returned from valid sign is returned in ``signer_details``, but in the example
        above only the ``type`` and ``signers`` attributes are shown.

        """

        logger.debug(
            f"Retrieving details to sign documents in ValidSign package '{package.get('id')}'"
        )

        signers = self._get_signers_from_package(package)

        details_for_signers = []
        for signer in signers:
            get_url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/roles/{signer.get('id')}/signingUrl"
            response = requests.get(get_url, headers=self._auth_header)
            response.raise_for_status()
            signing_url_details = response.json()
            # Adds the details of each signer
            signing_url_details.update({"signer_details": signer})
            details_for_signers.append(signing_url_details)

        return details_for_signers

    def perform(self) -> dict:
        package = self.create_package()
        documents = self.add_documents_to_package(package)
        self.create_approval_for_documents(package, documents)
        self.send_package(package)
        details = self.get_signing_details(package)

        return {"signing_details": details}
