import functools
import traceback
from typing import Optional

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


def retry(times=3, exceptions=(Exception,), condition: callable = lambda exc: True):
    """
    Retry the decorated callable up to ``times`` if it raises a known exception.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tries_left = times + 1

            while tries_left > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    # the extra exception check doesn't pass, so consider it an
                    # unexpected exception
                    if not condition(exc):
                        raise
                    else:  # expected exception, retry (if there are retries left)
                        tries_left -= 1

                    # if we've reached the maximum number of retries, raise the
                    # exception again
                    if tries_left < 1:
                        raise

        return wrapper

    return decorator
