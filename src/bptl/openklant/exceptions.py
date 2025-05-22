class OpenKlantEmailException(Exception):
    """Custom exception raised when email sending fails."""

    def __init__(self, message="Failed to send email."):
        super().__init__(message)


class EmailSendFailedException(Exception):
    """Custom exception raised when email sending fails."""

    def __init__(self, message="Failed to send email"):
        super().__init__(message)
