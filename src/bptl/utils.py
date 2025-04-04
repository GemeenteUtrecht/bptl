import functools
import inspect
import logging
import time
from functools import wraps

from django.core.cache import caches

import requests

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
