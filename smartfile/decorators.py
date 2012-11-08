from functools import wraps

from requests.exceptions import RequestException

from smartfile.exceptions import SmartFileConnException
from smartfile.exceptions import SmartFileResponseException


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
