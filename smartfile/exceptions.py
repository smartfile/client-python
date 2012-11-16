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
            self.detail = u'{0}: {1}'.format(exc.__class__, exc)
        super(SmartFileConnException, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.detail


class SmartFileResponseException(SmartFileException):
    """ Exception for issues regarding a response. """
    def __init__(self, response, *args, **kwargs):
        self.response = response
        self.status_code = response.status_code
        if not response.json or not 'detail' in response.json:
            self.detail = u'Server error; check response for errors'
        else:
            self.detail = response.json['detail']
        super(SmartFileResponseException, self).__init__(*args, **kwargs)

    def __str__(self):
        return 'Response {0}: {1}'.format(self.status_code, self.detail)
