import functools
import inspect
import logging
import time
import traceback
from functools import wraps

from django.core.cache import caches

import requests
from timeline_logger.models import TimelineLog

from .constants import Statuses

logger = logging.getLogger(__name__)


def cache(key: str, alias: str = "default", **set_options):
    def decorator(func: callable):
        argspec = inspect.getfullargspec(func)

        if argspec.defaults:
            positional_count = len(argspec.args) - len(argspec.defaults)
            defaults = dict(zip(argspec.args[positional_count:], argspec.defaults))
        else:
            defaults = {}

        @wraps(func)
        def wrapped(*args, **kwargs):
            skip_cache = kwargs.pop("skip_cache", False)
            if skip_cache:
                return func(*args, **kwargs)

            key_kwargs = defaults.copy()
            named_args = dict(zip(argspec.args, args), **kwargs)
            key_kwargs.update(**named_args)

            if argspec.varkw:
                var_kwargs = {
                    key: value
                    for key, value in named_args.items()
                    if key not in argspec.args
                }
                key_kwargs[argspec.varkw] = var_kwargs

            cache_key = key.format(**key_kwargs)

            _cache = caches[alias]
            result = _cache.get(cache_key)
            if result is not None:
                logger.debug("Cache key '%s' hit", cache_key)
                return result

            result = func(*args, **kwargs)
            _cache.set(cache_key, result, **set_options)
            return result

        return wrapped

    return decorator


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
    exponential_rate=1.0,
    max_times=10,
    max_backoff=30,
    exceptions=(Exception,),
    condition: callable = lambda exc: True,
    delay=1.0,
    on_failure: callable = lambda exc, *args, **kwargs: None,
):
    """
    Retry the decorated callable up to ``times`` if it raises a known exception.

    If the retries are all spent, then on_failure will be invoked.

    Idiot proof
    Default max times = 10
    Default max backoff = 30 seconds
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tries_left = min(times, max_times) + 1
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

                backoff = delay * pow(
                    exponential_rate, min(times, max_times) - tries_left
                )
                backoff = min(backoff, max_backoff)
                time.sleep(backoff)

        return wrapper

    return decorator
