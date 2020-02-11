from typing import Callable, List

from django.conf import settings
from django.core.management import BaseCommand

from tqdm import tqdm

from bptl.tasks.api import execute

from ...api import complete
from ...constants import Statuses
from ...models import ExternalTask
from ...utils import fetch_and_lock


class Command(BaseCommand):
    help = """Fetch, execute and complete a number of Camunda tasks.
    This command includes 3 steps:
    1. Fetch and lock external tasks. This step is similar to `fetch_and_lock_tasks` command'
    2. Execute fetched tasks using registered callbacks (python classes of functions)
    3. Send the results of successfully executed tasks back to Camunda.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "max_tasks", type=int, help="Maximum number of tasks to execute"
        )

    def run_callback_for_tasks(
        self, tasks: List[ExternalTask], callback: Callable, name: str
    ) -> List[ExternalTask]:
        self.stdout.write(f"Start '{name}' step", self.style.MIGRATE_LABEL)

        succeeded = []
        for task in tqdm(tasks, disable=settings.TQDM_DISABLED):
            try:
                callback(task)
            except Exception as exc:
                self.stdout.write(f"Task {task} has failed during {name}: {exc}")

                task.status = Statuses.failed
                task.save()
            else:
                succeeded.append(task)

        self.stdout.write(f"{len(succeeded)} task(s) succeeded during {name}")
        self.stdout.write(f"{len(tasks) - len(succeeded)} task(s) failed during {name}")
        self.stdout.write("\n")

        return succeeded

    def handle(self, **options):
        # fetch and lock tasks
        self.stdout.write(f"Start 'fetch and lock' step", self.style.MIGRATE_LABEL)

        worker_id, fetched_amount, fetched = fetch_and_lock(options["max_tasks"])

        self.stdout.write(
            f"{fetched_amount} task(s) fetched with worker ID {worker_id}"
        )
        self.stdout.write("\n")

        # execute task
        executed = []
        if fetched:
            executed = self.run_callback_for_tasks(fetched, execute, "execution")

        # complete task
        if executed:
            completed = self.run_callback_for_tasks(
                executed, complete, "sending process"
            )
