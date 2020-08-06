from django.core.management import BaseCommand

import requests
from django_camunda.client import get_client


class Command(BaseCommand):
    help = "Delete one or more process instances"

    def add_arguments(self, parser):
        parser.add_argument("--definition-id", help="Process definition ID")

    def handle(self, **options):
        client = get_client()

        query = None
        if options["definition_id"]:
            query = {"processDefinitionId": options["definition_id"]}

        if query is None:
            self.stderr.write("No query given.")
            return

        instances = client.get("process-instance", query)
        for instance in instances:
            _id = instance["id"]
            self.stdout.write(f"Deleting instance {_id}")
            try:
                client.delete(f"process-instance/{_id}")
            except requests.HTTPError as exc:
                if exc.response.status_code == 404:
                    self.stderr.write(f"Instance with ID {_id} not found.")
                    continue
                raise
            self.stdout.write(f"Deleted instance {_id}")

        self.stdout.write("Deletion completed.")
