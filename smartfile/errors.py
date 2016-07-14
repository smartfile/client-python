import six


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
            if self.status_code == 404:
                self.detail = six.u('Invalid URL, check your API path')
            else:
                self.detail = six.u('Server error; check response for errors')
        else:
            if self.status_code == 400 and 'field_errors' in json:
                self.detail = json['field_errors']
            else:
                try:
                    # A faulty move request returns the below response
                    self.detail = json['src'][0]
                except KeyError:
                    # A faulty delete request returns the below response
                    try:
                        self.detail = json['path'][0]
                    except KeyError:
                        self.detail = six.u('Error: %s' % response.content)
        super(ResponseError, self).__init__(*args, **kwargs)

    def __str__(self):
        return 'Response {0}: {1}'.format(self.status_code, self.detail)
