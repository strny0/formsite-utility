"""Defines the FormFetcher object and its logic."""

from time import sleep
from typing import Generator
from math import ceil
from requests import Session, Response, HTTPError
from requests.exceptions import ConnectionError as requests_ConnectionError
from formsite_util.error import (
    FormsiteForbiddenException,
    FormsiteFormNotFoundException,
    FormsiteInternalException,
    FormsiteInvalidAuthenticationException,
    FormsiteInvalidParameterException,
    FormsiteRateLimitException,
)
from formsite_util.logger import FormsiteLogger
from formsite_util.parameters import FormsiteParameters
from formsite_util.consts import ConnectionError_DELAY, HTTP_429_WAIT_DELAY


class FormFetcher:
    """Performs API Interaction"""

    def __init__(
        self,
        form_id: str,
        token: str,
        server: str,
        directory: str,
        params: FormsiteParameters,
    ):
        """FormFetcher constructor

        Args:
            form_id (str): FormsiteForm ID
            token (str): Formsite API access token
            server (str): Formsite server (fsX.formsite. ...)
            directory (str): Forms directory
            params (FormsiteParameters): Results fetch parameters
        """
        self.form_id = form_id
        self.params = params
        self.results_params = params.as_dict()
        # ----
        self.url_base: str = f"https://{server}.formsite.com/api/v2/{directory}"
        self.url_results = f"{self.url_base}/forms/{self.form_id}/results"
        self.url_items = f"{self.url_base}/forms/{self.form_id}/items"
        self.auth_header = {"Authorization": f"bearer {token}"}
        # ----
        self.total_pages = 1
        self.cur_page = 1
        self.logger: FormsiteLogger = FormsiteLogger()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.form_id}>"

    def fetch_iterator(self) -> Generator[dict, None, None]:
        """Iterates through all HTTP response pages

        Yields:
            Generator[dict]: data_of_page
        """
        max_page_sz = 500
        page_sz = self.results_params.get("limit", max_page_sz)
        with Session() as session:
            session.headers.update(self.auth_header)
            while True:
                try:
                    if self.cur_page > self.total_pages:
                        return StopIteration
                    resp = self.fetch_result(self.cur_page, session)
                    self.handle_response(resp)
                    self.total_pages = int(resp.headers.get("Pagination-Page-Last"))
                    self.total_pages = min(ceil(page_sz / max_page_sz), self.total_pages)
                    self.logger.debug(
                        f"Formsite API fetch {self.form_id} results | {self.cur_page}/{self.total_pages}"
                    )
                    self.cur_page += 1
                    yield resp.json()
                except FormsiteRateLimitException:
                    self.logger.debug(
                        f"Formsite API fetch reached RateLimitException | waiting {HTTP_429_WAIT_DELAY} seconds"
                    )
                    sleep(HTTP_429_WAIT_DELAY)

    def fetch_result(self, page: int, session: Session) -> Response:
        """Fetches a particular page of results

        Args:
            page (int): Current result page to fetch
            session (Session): Existing authorized session

        Returns:
            Response: Closed requests.Response object
        """
        params = self.results_params.copy()
        params["page"] = page
        try:
            with session.get(self.url_results, params=params) as resp:
                return resp
        except requests_ConnectionError:
            self.logger.critical(
                f"API Fetch {self.form_id}: Target refused connection, waiting and retrying"
            )
            sleep(ConnectionError_DELAY)
            return self.fetch_result(page, session)

    def fetch_items(self, results_labels_id: int = None) -> dict:
        """Fetches form items

        Args:
            results_labels_id (int, optional): Fetch result labels of this particular id. Defaults to None.

        Returns:
            dict: Formsite form's items dictionary
        """
        with Session() as session:
            session.headers.update(self.auth_header)
            params = (
                {"results_labels": results_labels_id}
                if results_labels_id is not None
                else {}
            )
            with session.get(self.url_items, params=params) as resp:
                self.handle_response(resp)
                self.logger.debug(f"Formsite API fetch: {self.form_id} items")
                return resp.json()

    @staticmethod
    def handle_response(response: Response):
        """Handles HTTP Repsonse code"""
        if response.status_code == 200:
            pass
        elif response.status_code == 401:  # Authentication info is missing or invalid.
            raise FormsiteInvalidAuthenticationException(
                response,
                "Please check if token, directory and server are correct",
            )
        elif response.status_code == 403:  # Forbidden.
            raise FormsiteForbiddenException(response.text)
        elif response.status_code == 404:  # Path or object not found.
            raise FormsiteFormNotFoundException(response.text)
        elif response.status_code == 422:  # Invalid parameter.
            raise FormsiteInvalidParameterException(response.text)
        elif response.status_code == 429:  # Too many requests or too busy.
            raise FormsiteRateLimitException(response.text)
        elif response.status_code >= 500:  # Unexpected Formsite internal error.
            raise FormsiteInternalException(response.text)
        else:
            raise HTTPError(response.text)
