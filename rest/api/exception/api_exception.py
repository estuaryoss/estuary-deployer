class ApiException(Exception):
    """
    Exception raised for api errors.

    Attributes:
        code -- api error code
        message -- explanation of the exception
        exception -- root exception
    """

    def __init__(self, code, message, exception):
        self.code = code
        self.message = message
        self.exception = exception
        super().__init__(self.message)
