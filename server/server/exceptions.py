"""
    Define custom exceptions for handling specific error cases.
    InvalidPayloadError: Exception raised when the payload is invalid.
    SearchFileReadError: Exception raised when there is an error reading the search file.
"""


class InvalidPayloadError(Exception):
    """
    Exception raised when the payload is invalid.
    """
    def __init__(self, message="Invalid payload"):
        self.message = message
        super().__init__(self.message)

class SearchFileReadError(Exception):
    """
    Exception raised when there is an error reading the search file.
    """
    def __init__(self, message="Error reading the search file"):
        self.message = message
        super().__init__(self.message)
        
class FileAccessError(Exception):
    """
    Exception raised when there is an error accessing the file.
    """
    def __init__(self, message="Error accessing the file"):
        self.message = message
        super().__init__(self.message)