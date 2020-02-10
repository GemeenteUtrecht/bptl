from django.core.management import BaseCommand

from ...registry import register


class Command(BaseCommand):
    help = "Introspect the task registry"

    def handle(self, **options):
        for task in register:
            lines = [f"  {line}" for line in task.documentation.splitlines()]
            doc = "\n".join(lines)

            self.stdout.write(task.dotted_path, self.style.MIGRATE_LABEL)
            self.stdout.write("\n")
            self.stdout.write(doc)
            self.stdout.write("\n")
