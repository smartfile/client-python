from requests.exceptions import ConnectionError


class SmartFileException(Exception):
    pass


class SmartFileConnException(SmartFileException):
    """ Exception for issues regarding a request. """
    def __init__(self, exc, *args, **kwargs):
        self.exc = exc
        if isinstance(exc, ConnectionError):
            self.detail = exc.message.strerror
        else:
            self.detail = '{0}: {1}'.format(exc.__class__, exc)
        super(SmartFileConnException, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.detail


class SmartFileResponseException(SmartFileException):
    """ Exception for issues regarding a response. """
    def __init__(self, response, *args, **kwargs):
        self.response = response
        self.status_code = response.status_code
        self.detail = response.json.get('detail', 'Check response for errors')
        super(SmartFileResponseException, self).__init__(*args, **kwargs)

    def __str__(self):
        return 'Response {0}: {1}'.format(self.status_code, self.detail)
