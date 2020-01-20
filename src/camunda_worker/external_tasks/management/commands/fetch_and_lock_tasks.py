from django.core.management import BaseCommand

from ...camunda import fetch_and_lock


class Command(BaseCommand):
    help = "Fetch and lock a number of external tasks. Topics are retrieved randomly."

    def add_arguments(self, parser):
        parser.add_argument(
            "max_tasks", type=int, help="Maximum number of tasks to fetch and lock."
        )

    def handle(self, **options):
        worker_id, amount, tasks = fetch_and_lock(options["max_tasks"])
        self.stdout.write(f"{amount} task(s) saved with worker ID {worker_id}")
