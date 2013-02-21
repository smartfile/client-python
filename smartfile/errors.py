

class APIError(Exception):
    "SmartFile API base Exception."
    pass


class RequestError(APIError):
    """ Exception for issues regarding a request. """
    def __init__(self, exc, *args, **kwargs):
        self.exc = exc
        self.detail = str(exc)
        super(RequestError, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.detail


class ResponseError(APIError):
    """ Exception for issues regarding a response. """
    def __init__(self, response, *args, **kwargs):
        self.response = response
        self.status_code = response.status_code
        try:
            json = response.json()
        except ValueError:
            pass
        else:
            if not json or not 'detail' in json:
                self.detail = u'Server error; check response for errors'
            elif self.status_code == 400:
                self.detail = json['field_errors']
            else:
                self.detail = json['detail']
        super(ResponseError, self).__init__(*args, **kwargs)

    def __str__(self):
        return 'Response {0}: {1}'.format(self.status_code, self.detail)
