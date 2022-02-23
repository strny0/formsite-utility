"""

form_error.py

"""

from requests import HTTPError


class FormsiteNoResultsException(Exception):
    """No results in specified parameters"""


class InvalidDateFormatExpection(Exception):
    """Entered invalid date format for after_date or before_date parameter"""


class FormsiteInvalidAuthenticationException(HTTPError):
    """Invalid token, server or directory"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FormsiteFormNotFoundException(HTTPError):
    """Invalid form id"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FormsiteInvalidParameterException(HTTPError):
    """Invalid parameter passed to request"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FormsiteRateLimitException(HTTPError):
    """Reached Formsite API rate limit, please wait at least 50 seconds"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FormsiteInternalException(HTTPError):
    """Unexpected error on FormSite servers (HTTP 5xx)"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FormsiteForbiddenException(HTTPError):
    """HTTP 403 Error"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FormsiteFileDownloadException(HTTPError):
    """Exception occured while downloading a file from formsite form"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FormsiteUncachableParametersException(Exception):
    """FormsiteForm was fetched with use_items=True or not fetched at all"""


class InvalidItemsStructureException(Exception):
    """FormsiteForm or FormData .items property is set incorrectly"""
