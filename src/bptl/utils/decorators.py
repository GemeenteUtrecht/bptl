import functools
import traceback

from timeline_logger.models import TimelineLog

from .constants import Statuses


def save_and_log(status=Statuses.performed):
    def inner(func):
        @functools.wraps(func)
        def wrapper(task, *args, **kwargs):
            try:
                result = func(task, *args, **kwargs)
            except Exception as exc:
                task.status = Statuses.failed
                task.execution_error = traceback.format_exc()
                task.save(update_fields=["status", "execution_error"])

                TimelineLog.objects.create(
                    content_object=task, extra_data={"status": task.status}
                )

                raise

            else:
                task.status = status
                if status == Statuses.performed:
                    task.result_variables = result
                task.save(update_fields=["status", "result_variables"])

                TimelineLog.objects.create(
                    content_object=task, extra_data={"status": task.status}
                )

            return result

        return wrapper

    return inner
