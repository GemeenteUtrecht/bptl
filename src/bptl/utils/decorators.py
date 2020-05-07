import functools
import logging
import time
import traceback

from timeline_logger.models import TimelineLog

from .constants import Statuses

logger = logging.getLogger(__name__)


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


def retry(
    times=3,
    exceptions=(Exception,),
    condition: callable = lambda exc: True,
    delay=1.0,
    on_failure: callable = lambda exc, *args, **kwargs: None,
):
    """
    Retry the decorated callable up to ``times`` if it raises a known exception.

    If the retries are all spent, then on_failure will be invoked.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tries_left = times + 1

            logger.info("Tries left: %d, %r", tries_left, func)

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
                        logger.error("Task didn't succeed after %d retries", times)
                        on_failure(exc, *args, **kwargs)
                        raise

                time.sleep(delay)

        return wrapper

    return decorator
