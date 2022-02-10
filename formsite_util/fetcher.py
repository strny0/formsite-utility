"""

fetch.py


"""


import sys
from time import sleep
from typing import Generator, Tuple
from requests import Response, HTTPError
from formsite_util.form_error import (
    FormsiteForbiddenException,
    FormsiteFormNotFoundException,
    FormsiteInternalException,
    FormsiteInvalidAuthenticationException,
    FormsiteInvalidParameterException,
    FormsiteRateLimitException,
)
from formsite_util.parameters import FormsiteParameters
from formsite_util.session import FormsiteSession

HTTP_429_WAIT_DELAY = 60  # seconds

ceil = lambda x: int(-(-x // 1))


class FormFetcher:
    """Performs API Interaction"""

    def __init__(
        self,
        form_id: str,
        session: FormsiteSession,
        params: FormsiteParameters,
    ):
        """FormFetcher constructor

        Args:
            form_id (str): Formsite Form ID
            session (FormsiteSession): FormsiteSession object
        """
        self.form_id = form_id
        self.session = session
        self.params = params
        self.results_params = params.results_params_dict()
        self.items_params = params.items_params_dict()
        self.results_url = f"{session.url_base}/forms/{self.form_id}/results"
        self.items_url = f"{session.url_base}/forms/{self.form_id}/items"

    def __repr__(self) -> str:
        return f"<FormFetcher {self.form_id} | {self.session.url_base}>"

    def fetch_iterator(self) -> Generator[Tuple[int, dict], None, None]:
        """Iterates through all HTTP response pages

        Yields:
            Generator[int, dict]: (total_pages, data_of_page)
        """
        page: int = 1
        page_limit: int = 1
        results_per_page = self.results_params.get("limit", 500)
        last_limit = self.params.last if self.params.last is not None else sys.maxsize
        while True:
            try:
                if page > page_limit:
                    return StopIteration
                if last_limit and page > ceil(last_limit / results_per_page):
                    return StopIteration
                response = self.fetch_result(page)
                self.handle_response(response)
                page += 1
                page_limit = int(response.headers.get("Pagination-Page-Last"))
                yield response.json(), page_limit

            except FormsiteRateLimitException:
                sleep(HTTP_429_WAIT_DELAY)

    def fetch_result(self, page: int) -> Response:
        """Fetches a particular page of results"""
        params = self.results_params.copy()
        params["page"] = page
        response = self.session.get(self.results_url, params)
        return response

    def fetch_items(self) -> dict:
        """Fetches form items"""
        response = self.session.get(self.items_url, self.items_params)
        self.handle_response(response)
        return response.json()

    def handle_response(self, response: Response):
        """Handles HTTP Repsonse code"""
        if response.status_code == 200:
            pass
        elif response.status_code == 401:  # Authentication info is missing or invalid.
            raise FormsiteInvalidAuthenticationException(response)
        elif response.status_code == 403:  # Forbidden.
            raise FormsiteForbiddenException(response)
        elif response.status_code == 404:  # Path or object not found.
            raise FormsiteFormNotFoundException(response)
        elif response.status_code == 422:  # Invalid parameter.
            raise FormsiteInvalidParameterException(response)
        elif response.status_code == 429:  # Too many requests or too busy.
            raise FormsiteRateLimitException(response)
        elif response.status_code >= 500:  # Unexpected Formsite internal error.
            raise FormsiteInternalException(response)
        else:
            raise HTTPError(response)
