class LocationError(Exception):
    """Exception raised for errors related to fetching location.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class DataFetchError(Exception):
    """Exception raised for errors related to fetching latest data.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class InvalidDataError(Exception):
    """Exception raised for errors related to the contents of the data.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
