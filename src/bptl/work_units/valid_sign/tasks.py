import json
import uuid
from typing import List, Tuple

from django.conf import settings

import requests

from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register


@register
class ValidSignTask(WorkUnit):
    """
    Takes a set of documents and a set of signers and uses the ValidSign signing
    process to make the signers digitally sign all the documents.

    **Required process variables**

    * ``documents``: list of API URLs where the documents to be signed can be retrieved.
        The API should provide the document name and the content.

    * ``signers``: list of API URLs where details of the signers can be retrieved.
        The API should provide at least the first name, the last name and the email address of the signer.

    """

    _auth_header = {"Authorization": f"Basic {settings.VALIDSIGN_APIKEY}"}

    def _get_signers_from_api(self) -> List[dict]:
        """
        Gets information about the signers and formats it as needed by ValidSign
        """

        # TODO retrieve signer info from API
        test_signers = [
            {
                "id": "test-signer-1-id",
                "name": "Test Signer 1",
                "type": "SIGNER",
                "index": 0,
                "signers": [
                    {
                        "id": "test-signer-1-id",
                        "company": "Test Company",
                        "email": "test.signer1@example.com",
                        "firstName": "Test name 1",
                        "lastName": "Test surname 1",
                        "phone": "000000000000",
                        "title": "Consultant",
                        "address": None,
                        "language": "nl",
                        "name": "Test Signer 1",
                        "auth": {"challenges": [], "scheme": "NONE"},
                        "knowledgeBasedAuthentication": None,
                        "delivery": {
                            "email": True,
                            "download": True,
                            "provider": False,
                        },
                    }
                ],
            },
            {
                "id": "test-signer-2-id",
                "name": "Test Signer 2",
                "type": "SIGNER",
                "index": 1,
                "signers": [
                    {
                        "id": "test-signer-2-id",
                        "company": "Test Company",
                        "email": "test.signer2@example.com",
                        "firstName": "Test name 2",
                        "lastName": "Test surname 2",
                        "phone": "000000000000",
                        "title": "Consultant",
                        "address": None,
                        "language": "nl",
                        "name": "Test Signer 2",
                        "auth": {"challenges": [], "scheme": "NONE"},
                        "knowledgeBasedAuthentication": None,
                        "delivery": {
                            "email": True,
                            "download": True,
                            "provider": False,
                        },
                    }
                ],
            },
        ]

        return test_signers

    def _get_documents_from_api(self) -> List[Tuple[str, bytes]]:
        """
        Retrieves the documents from Documenten API and returns a list of the name and the binary content
        of each document.
        """
        variables = self.task.get_variables()

        document_urls = variables.get("documents")

        documents = []
        for document_url in document_urls:
            # Retrieving the document
            response = requests.get(
                document_url,
                auth=(settings.PROEFTUIN_USER, settings.PROEFTUIN_PASSWORD),
            )
            document_data = response.json()
            # Retrieving the content of the document
            response = requests.get(
                document_data.get("inhoud"),
                auth=(settings.PROEFTUIN_USER, settings.PROEFTUIN_PASSWORD),
            )
            document_content = response.content

            documents.append((document_data.get("titel"), document_content))

        return documents

    def _get_signers_from_validsign(self, package: dict) -> List[dict]:
        """
        Retrieves all the roles from a ValidSign package and returns all the signers.
        """
        roles_url = (
            f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/roles"
        )
        response = requests.get(roles_url, headers=self._auth_header)
        roles = response.json().get("results")
        # Not all the roles are signers (one of them is the account owner)
        return [role for role in roles if role.get("type") == "SIGNER"]

    def create_package(self) -> dict:
        """
        Creates a ValidSign package with the signers and the settings
        for the signing ceremony.
        """

        signers = self._get_signers_from_api()

        url = f"{settings.VALIDSIGN_ROOT_URL}api/packages"

        body = {
            "name": f"Package {uuid.uuid1()}",
            "type": "PACKAGE",
            "language": "en",
            "emailMessage": "",
            "description": "Package created by BPTL",
            "roles": signers,
        }

        response = requests.post(url, headers=self._auth_header, data=json.dumps(body))
        package = response.json()

        return package

    def add_documents_to_package(self, package: dict) -> List[dict]:
        """
        Adds documents to the specified package and returns a list with the information about each document.
        """

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
            attached_documents.append(response.json())

        return attached_documents

    def create_approval_for_documents(self, package: dict, documents: List[dict]):
        """
        Creates an approval (a placeholder for where a signature will go) in the
        specified documents for all signers.
        """

        signers = self._get_signers_from_validsign(package)

        # Settings such as where the signature will be placed in the document, the type of the approval (signature)
        # TODO change the placement of the signature for each signer, otherwise they overlap
        approval_settings = [
            {
                "top": 50,
                "left": 300,
                "width": 200,
                "height": 50,
                "page": 0,
                "type": "SIGNATURE",
                "value": None,
                "subtype": "FULLNAME",
            }
        ]
        # For all the documents, create an approval for each signer
        for document in documents:
            approval_url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/documents/{document.get('id')}/approvals"
            for signer in signers:
                data = {"role": f"{signer.get('id')}", "fields": approval_settings}
                response = requests.post(
                    approval_url, data=json.dumps(data), headers=self._auth_header
                )

    def send_package(self, package: dict):
        """
        Changes the status of a package to "SENT".
        """
        url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}"
        body = {"status": "SENT"}
        requests.put(url, headers=self._auth_header, data=json.dumps(body))

    def get_signing_urls(self, package: dict) -> List[dict]:
        """
        Retrieves all the urls where each signer can go to sign the documents. Each url is returned as a dictionary
        with also the id of the signer and the id of the package.
        """
        signers = self._get_signers_from_validsign(package)

        signing_urls = []
        for signer in signers:
            get_url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}/roles/{signer.get('id')}/signingUrl"
            response = requests.get(get_url, headers=self._auth_header)
            signing_urls.append(response.json())

        return signing_urls

    def send_links_to_signers(self, urls: List[dict]):
        """
        Notifies all signers that there are documents to be signed and
        provides the links to them.
        """
        pass

    def get_package_info(self, package: dict) -> dict:
        """
        Regularly checks the status of a package after users have been sent the signing URL.
        When all the signers have signed, the status changes from 'SENT' to 'COMPLETED'
        """
        get_url = f"{settings.VALIDSIGN_ROOT_URL}api/packages/{package.get('id')}"
        respones = requests.get(get_url, headers=self._auth_header)
        package_info = respones.json()

        status = package_info.get("status")

        while status != "COMPLETED":
            # TODO wait
            break

        return package_info

    def perform(self) -> dict:
        package = self.create_package()
        documents = self.add_documents_to_package(package)
        self.create_approval_for_documents(package, documents)
        self.send_package(package)
        urls = self.get_signing_urls(package)

        self.send_links_to_signers(urls)

        complete_package = self.get_package_info(package)

        return complete_package
