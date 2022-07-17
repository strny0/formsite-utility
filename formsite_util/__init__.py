"""

## High level interfaces

FormsiteParameters: Represents parameters for results/items requests

FormsiteForm: Represents the form data and session

FormsiteFormsList: Represents the list of all forms for the specified account

FormData: Represents the form data without session

FormsiteLogger: Custom logger you can connect to your own logging

## Internal interfaces

.internal.FormFetcher: Result/Item fetching operations

.internal.FormParser: Result/Item parsing operations

.internal.AsyncFormDownloader: 

.internal.DownloadStatus: 

## Legacy interfaces

.legacy.FormsiteCredentials

.legacy.FormsiteInterface

.legacy.FormsiteParams

"""
__version__ = "2.1.0"

from ._form import FormsiteForm
from ._list import FormsiteFormsList
from ._form_data import FormData
from ._parameters import FormsiteParameters
from ._logger import FormsiteLogger
