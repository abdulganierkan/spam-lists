# -*- coding: utf-8 -*-

"""Function and method argument validators used by the library."""
from __future__ import unicode_literals

import functools
import re

from future.moves.urllib.parse import urlparse
import validators

from .exceptions import InvalidURLError, InvalidHostError


def is_valid_host(value):
    """Check if given value is a valid host string.

    :param value: a value to test
    :returns: True if the value is valid
    """
    host_validators = validators.ipv4, validators.ipv6, validators.domain
    return any(f(value) for f in host_validators)


URL_REGEX = re.compile(r'^[a-z0-9\.\-\+]*://'  # scheme
                       r'(?:\S+(?::\S*)?@)?'  # authentication
                       r'(?:[^/:]+|\[[0-9a-f:\.]+\])'  # host
                       r'(?::\d{2,5})?'  # port
                       r'(?:[/?#][^\s]*)?'  # path, query or fragment
                       r'$', re.IGNORECASE)


def is_valid_url(value):
    """Check if given value is a valid URL string.

    :param value: a value to test
    :returns: True if the value is valid
    """
    match = URL_REGEX.match(value)
    host_str = urlparse(value).hostname
    return match and is_valid_host(host_str)


def accepts_valid_host(func):
    """Return a wrapper that runs given method only for valid hosts.

    :param func: a method to be wrapped
    :returns: a wrapper that adds argument validation
    """
    @functools.wraps(func)
    def wrapper(obj, value, *args, **kwargs):
        """Run the function and return a value for a valid host.

        :param obj: an object in whose class the func is defined
        :param value: a value expected to be a valid host string
        :returns: a return value of the function func
        :raises InvalidHostError: if the value is not valid
        """
        if not is_valid_host(value):
            raise InvalidHostError
        return func(obj, value, *args, **kwargs)
    return wrapper


def accepts_valid_urls(func):
    """Return a wrapper that runs given method only for valid URLs.

    :param func: a method to be wrapped
    :returns: a wrapper that adds argument validation
    """
    @functools.wraps(func)
    def wrapper(obj, urls, *args, **kwargs):
        """Run the function and return a value for valid URLs.

        :param obj: an object in whose class f is defined
        :param urls: an iterable containing URLs
        :returns: a return value of the function f
        :raises InvalidURLError: if the iterable contains invalid URLs
        """
        invalid_urls = [u for u in urls if not is_valid_url(u)]
        if invalid_urls:
            msg_tpl = 'The values: {} are not valid URLs'
            msg = msg_tpl.format(','.join(invalid_urls))
            raise InvalidURLError(msg)
        return func(obj, urls, *args, **kwargs)
    return wrapper
