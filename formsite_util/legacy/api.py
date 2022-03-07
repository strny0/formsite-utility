"""
api.py

This module contains a class that handles API requests to Formsite API.
"""
from __future__ import annotations
from typing import List, Tuple, Any
from dataclasses import dataclass
import time
import requests
from requests.exceptions import HTTPError
from tqdm import tqdm

from .auth import FormsiteCredentials


@dataclass
class _FormsiteAPI:
    """Handles retreival of results from your formsite form. Invoked with `self.Start()` method.

    Keywords:
        Results: Data from your formsite form (the rows).
        Items:   Labels of user-defined columns in your formsite form (the header row).

    Args:
        form_id (str): ID of form to fetch.
        params (FormsiteParams): An instance of FormsiteParams class.
        auth (FormsiteCredentials): An instance of FormsiteCredentials class.
        display_progress (bool): Display progress using tqdm. Defaults to True.
        delay (float | int): Delay in seconds between each API call. Defaults to 5.
        long_delay (float | int): Delay in seconds between each API call after page 3. Defaults to 15.

    Raises:
        Exception: General uncaught exception.
        HTTPError: Raised for all HTTP response codes other than 200 or 429.

    Returns:
        _FormsiteAPI: Instance of the _FormsiteAPI class. Start requests in `.Start()` method.
    """

    form_id: str
    params: Any
    auth: FormsiteCredentials
    display_progress: bool = True
    short_delay: float = 5.0
    long_delay: float = 15.0

    def __post_init__(self):
        """Generates post_init internal variables."""
        self.url_base: str = (
            f"https://{self.auth.server}.formsite.com/api/v2/{self.auth.directory}"
        )
        self.results_url: str = f"{self.url_base}/forms/{self.form_id}/results"
        self.items_url: str = f"{self.url_base}/forms/{self.form_id}/items"
        self.total_pages: int = 1
        self.check_pages: bool = True
        self.pbar = (
            tqdm(
                desc="Starting API requests",
                total=2,
                unit="call",
                leave=False,
                dynamic_ncols=True,
                ncols=80,
            )
            if self.display_progress
            else None
        )
        self.session = None
        self.params_dict = self.params.get_params_as_dict()
        self.items_dict = self.params.get_items_as_dict()

    def Start(self, get_items: bool, get_results: bool) -> Tuple[dict, List[dict]]:
        """Performs all API calls to formsite servers asynchronously"""
        items, results = (None, [])
        with requests.session() as self.session:
            self.session.headers.update(self.auth.get_auth_header())
            results = self.get_results() if get_results else []
            items = self.fetch_items() if get_items else None
            self._update_pbar_progress()
            self._update_pbar_desc(desc="API calls complete")
            try:
                self.pbar.close()
            except AttributeError:
                pass
        return items, results

    def get_results(self) -> List[dict]:
        """Fetches all results that match input parameters from a form.

        Raises:
            HTTPError

        Returns:
            List[dict]: List of pages of results.
        """
        results = [self.fetch_results(self.params_dict, 1)]
        if self.total_pages > 1:
            for page in range(2, self.total_pages + 1):
                try:
                    if isinstance(self.params.last, int):
                        if (page * self.params_dict["limit"]) >= self.params.last:
                            self._update_pbar_total(page)
                            break
                    results.append(self.fetch_results(self.params_dict, page))
                except Exception as err:
                    print("\r\n")
                    print(err)
                    try:
                        del self.params_dict["after_id"]
                    except KeyError:
                        pass
                    try:
                        self.params_dict["before_id"] = int(
                            results[-1]["results"][-1]["id"]
                        )
                        print(
                            f"Retrying and resuming from {int(results[-1]['results'][-1]['id'])}"
                        )
                        self.long_delay *= 2  # double
                        results += self.get_results()
                        break
                    except KeyError:
                        print(
                            "Selected results view does not have 'Reference #' column. Unable to resume download."
                        )
                        raise Exception(
                            "This download is too intense for Formsite servers at the moment. Try using a results view or parameters to only get the results you need."
                        )
                    except Exception as err:
                        print(
                            "This download is too intense for Formsite servers at the moment. Try using a results view or parameters to only get the results you need."
                        )
                        raise err
        return results

    def fetch_results(self, params: dict, page: int) -> dict:
        """Handles fetching and writing (if selected) of results json."""
        self._update_pbar_desc(desc=f"Fetching rows ({(page-1)*500}-{page*500})")
        return self.fetch_content(self.results_url, params, page=page)

    def fetch_content(self, url: str, params: dict, page: int = None) -> dict:
        """Base method for interacting with the formsite api with aiohttp GET request. Returns content of the response."""
        if page is not None:
            params["page"] = page
            if page > 3:
                self._update_pbar_desc(
                    desc=f"Delay [{self.long_delay:0.0f} s] ({(page-1)*500}-{page*500})"
                )
                _ = time.sleep(max(self.long_delay - self.short_delay, 0))
            else:
                self._update_pbar_desc(
                    desc=f"Delay [{self.short_delay:0.0f} s] ({(page-1)*500}-{page*500})"
                )
        time.sleep(self.short_delay)
        with self.session.get(url, params=params) as response:
            content = response.json()
            if response.status_code != 200:
                previous_desc = self.pbar.desc
                self._update_pbar_desc(desc=f"Error: [{response.status_code}]")
                if response.status_code == 429:
                    self._update_pbar_desc(desc="Reached rate limit, waiting 60 seconds")
                    time.sleep(60)
                    self._update_pbar_desc(desc=previous_desc)
                    content = self.fetch_content(url, params, page=page)
                else:
                    err_message = f"[HTTP ERROR {response.status_code}] {response.text} for url '{response.url}'"
                    raise HTTPError(response, err_message)
            if self.check_pages and page is not None:
                self.total_pages = int(response.headers["Pagination-Page-Last"])
                self.check_pages = False
                try:
                    self._update_pbar_total(self.total_pages)
                except AttributeError as ex:
                    # print(ex)
                    pass
        self._update_pbar_progress()
        return content

    def fetch_items(self) -> dict:
        """Handles fetching and writing (if selected) of items json."""
        self._update_pbar_desc(desc="Fetching headers")
        return self.fetch_content(self.items_url, self.items_dict)

    def _update_pbar_total(self, n: int) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.total = n

    def _update_pbar_progress(self) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.update(1)

    def _update_pbar_desc(self, desc: str) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.set_description(desc=desc, refresh=True)
