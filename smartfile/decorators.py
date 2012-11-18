import re
import time

from functools import wraps

from requests.exceptions import RequestException

from smartfile.exceptions import SmartFileConnException
from smartfile.exceptions import SmartFileResponseException


def throttle_wait(func=None, throttle=True):
    """
    Make a request but try again if the client has hit the throttle.  This can
    made to just make the request by passing False for throttle.  The time to
    wait to make another attempt is taken from the time passed back by the
    server within the 'x-throttle' header.  This call will not return until it
    receives a non-throttled response.

    Usage:
        @throttle_wait
        @throttle_wait(throttle=False)
    """
    if func is None:
        def _func_wrap(func):
            @wraps(func)
            def _throttle_wait(*args, **kwargs):
                _throttle = throttle
                while True:
                    response = func(*args, **kwargs)
                    if _throttle and response.status_code == 503:
                        wait = re.search('next=([^ ]+) sec',
                                         response.headers['x-throttle'])
                        time.sleep(float(wait.group(1)))
                    else:
                        break
                return response
            return _throttle_wait
        return _func_wrap
    else:
        return throttle_wait(throttle=throttle)(func)


def response_processor(func):
    """
    Return a SmartFile exception if an exception issued by Requests is raised
    due to the request or an HTTP status code of 400 or greater is returned.
    """
    @wraps(func)
    def _response(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
        except RequestException as e:
            raise SmartFileConnException(e)
        else:
            if response.status_code >= 400:
                raise SmartFileResponseException(response)
        return response

    return _response
