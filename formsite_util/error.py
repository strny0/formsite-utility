"""Definitions of all custom exception classes."""

from requests import HTTPError


class FormsiteNoResultsException(Exception):
    """No results in specified parameters"""


class InvalidDateFormatExpection(Exception):
    """Entered invalid date format for after_date or before_date parameter"""


class FormsiteInvalidAuthenticationException(HTTPError):
    """Invalid token, server or directory"""


class FormsiteFormNotFoundException(HTTPError):
    """Invalid form id"""


class FormsiteInvalidParameterException(HTTPError):
    """Invalid parameter passed to request"""


class FormsiteRateLimitException(HTTPError):
    """Reached Formsite API rate limit, please wait at least 50 seconds"""


class FormsiteInternalException(HTTPError):
    """Unexpected error on FormSite servers (HTTP 5xx)"""


class FormsiteForbiddenException(HTTPError):
    """HTTP 403 Error"""


class FormsiteFileDownloadException(HTTPError):
    """Exception occured while downloading a file from formsite form"""


class FormsiteUncachableParametersException(Exception):
    """FormsiteForm was fetched with use_items=True or not fetched at all"""


class InvalidItemsStructureException(Exception):
    """FormsiteForm or FormData .items property is set incorrectly"""
