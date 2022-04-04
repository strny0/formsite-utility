"""

## High level interfaces

FormsiteParameters: Represents parameters for results/items requests

FormsiteForm: Represents the form data and session

FormsiteFormsList: Represents the list of all forms for the specified account

FormCache: Store formsite forms in a folder

## Low level interfaces

FormFetcher: Result/Item fetching operations

FormParser: Result/Item parsing operations

FormData: Represents the form data without session

FormsiteLogger: Custom logger you may connect to your own logging

"""
__version__ = "2.0.1"

from .form import FormsiteForm
from .list import FormsiteFormsList
from .parameters import FormsiteParameters
from .form_fetcher import FormFetcher
from .form_parser import FormParser
from .form_data import FormData

# Legacy functionality
from .legacy import FormsiteCredentials, FormsiteInterface, FormsiteParams
