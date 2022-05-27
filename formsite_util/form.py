"""Defines FormsiteForm object and its logic."""

from __future__ import annotations
import os
from pathlib import Path
from time import sleep
import re
from typing import Callable, Generator, List, Optional
import pandas as pd
from requests import Session

# ----
from formsite_util.error import FormsiteNoResultsException
from formsite_util.parameters import FormsiteParameters
from formsite_util.form_fetcher import FormFetcher
from formsite_util.form_parser import FormParser
from formsite_util.download import DownloadStatus, download_sync, filter_urls
from formsite_util.download_async import AsyncFormDownloader
from formsite_util.form_data import FormData
from formsite_util.cache import (
    items_load,
    items_match_data,
    items_save,
    results_load,
    results_save,
)


def tz_shif_inplace(df: pd.DataFrame, col: str, tz_name: str):
    """Converts a tz-aware dataframe column to target timezone"""
    if col in df:
        df[col] = df[col].dt.tz_convert(tz=tz_name)


class FormsiteForm(FormData):
    """Formsite API Form object, representing the data and HTTP session"""

    def __init__(
        self,
        form_id: str,
        token: str,
        server: str,
        directory: str,
        prepoulate_data: FormData = None,
    ):
        """FormsiteForm constructor

        Args:
            form_id (str): Formsite Form ID
            token (str): Formsite API Token
            server (str): Formsite Server (fsX.formsite.com)
            directory (str): Formsite Directory
            prepoulate_data (FormData, optional): Prepopulate form with this FormData object
        """

        super().__init__()
        self.form_id: str = form_id
        self.token: str = token
        self.server: server = server
        self.directory: directory = directory
        if prepoulate_data is not None:
            self._data = prepoulate_data._data
            self._items = prepoulate_data._items
            self._labels = prepoulate_data._labels

        self.logger.debug(f"Initialized {repr(self)}")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.form_id}>"

    def fetch(
        self,
        fetch_results: bool = True,
        fetch_items: bool = True,
        params: FormsiteParameters = FormsiteParameters(),
        result_labels_id: int = None,
        fetch_delay: float = 3.0,
        fetch_callback: Callable = None,
        # ---
        cache_items_path: str = None,
        cache_results_path: str = None,
    ):
        """Updates the FormsiteForm object instance with the data from Formsite accoridng to input params

        Fetch Args:
            fetch_results (bool, optional): Pull results within parameters. Defaults to True.
            fetch_items (bool, optional): Pull items (of resultslabels id). Defaults to True.
            params (FormsiteParameters): Pull results and items according to these parameters.
            result_labels_id (int, optional): Results labels id to use when fetching items. Defaults to None.
            fetch_delay (float): Time delay between individual API calls in seconds.
            fetch_callback (Callable, optional): Run this callback every time an API fetch is complete.

        Cache Args:
            cache_items_path (str) : Path where to store form items (as json). Defaults to None (will not store).
            cache_results_path (str) : Path where to store form results. Defaults to None (will not store).


        Supported Cache formats (file extensions) are:
            - parquet (recommended)
            - pkl | pickle
            - feather
            - hdf

        Callback funciton signature:
            function(cur_page: int, total_pages: int, data: dict) -> None
        """
        params = params.copy()
        self.logger.debug(f"{repr(self)} fetching with {params}")
        # -!- RESULTS PART
        parser = FormParser()
        fetcher = FormFetcher(
            self.form_id,
            self.token,
            self.server,
            self.directory,
            params,
        )
        if fetch_results:
            # ---- handle cache ----
            if cache_results_path is not None:
                if not isinstance(cache_results_path, str):
                    raise TypeError("Invalid path")
                cached_results = results_load(cache_results_path)
                if isinstance(cached_results, pd.DataFrame) and not cached_results.empty:
                    if "id" not in cached_results.columns:
                        raise ValueError(
                            "Expected stored data to have the 'id' (Reference #) column. Add this to your results view."
                        )
                    self.logger.debug(
                        f"Cache results {self.form_id}: Overwriting after_id:{max(cached_results['id'])} | before_id:None"
                    )
                    params.after_id = max(cached_results["id"])
                    params.before_id = None
                    fetcher.params = params
            # -!!- perform results fetch -!!-
            for data in fetcher.fetch_iterator():
                # --- edge case ---
                if not data.get("results") and not (
                    isinstance(cached_results, pd.DataFrame) and not cached_results.empty
                ):
                    raise FormsiteNoResultsException("No results in specified parameters")
                # --- regular case ---
                parser.feed(data)
                # --- callback ---
                if isinstance(fetch_callback, Callable):
                    fetch_callback(fetcher.cur_page, fetcher.total_pages, data)
                # --- fetch delay ---
                sleep(fetch_delay)
            # ---- finish handling cache ----
            if cache_results_path is not None:
                new_data = parser.as_dataframe()
                self.logger.debug(
                    f"Cache results {self.form_id}: Appending {new_data.shape[0]} new results"
                )
                # --- if there are new results, merge ---
                if new_data.shape[0] > 0:
                    merged_results = pd.concat(
                        [new_data, cached_results], ignore_index=True
                    )
                    merged_results = merged_results.reset_index(drop=True)
                    merged_results = merged_results.drop_duplicates(
                        subset=["id"],
                        keep="first",
                    )
                    self.data = merged_results
                    results_save(merged_results, cache_results_path)
                # --- otherwise just use the data we got ---
                else:
                    self.data = cached_results
            else:
                self.data = parser.as_dataframe()
            tz_shif_inplace(self.data, "date_update", params.timezone)
            tz_shif_inplace(self.data, "date_start", params.timezone)
            tz_shif_inplace(self.data, "date_finish", params.timezone)
            if params.last is not None:
                self.data = self.data.head(params.last)

        # -!- ITEMS PART
        if fetch_items:
            if cache_items_path is not None:
                if not isinstance(cache_items_path, str):
                    raise TypeError("Invalid path")
                cached_results = items_load(cache_items_path)
                if cached_results is None or not items_match_data(
                    cached_results, self.data.columns
                ):
                    self.logger.debug(
                        f"Cache items {self.form_id}: Fetching new items for cache"
                    )
                    cached_results = fetcher.fetch_items(result_labels_id)
                    items_save(cached_results, cache_items_path)
                self.items = cached_results
            else:
                self.items = fetcher.fetch_items(result_labels_id)
            self.labels = parser.create_rename_map(self.items)

    def downloader(
        self,
        download_dir: str,
        timeout: float = 160,
        max_attempts: int = 3,
        url_filter_re: str = r".+",
        filename_substitution_re_pat: str = r"",
        strip_prefix: bool = False,
        overwrite_existing: bool = True,
    ) -> Generator[DownloadStatus, None, None]:
        """Download files uploaded to the form via the File upload control (sequential)

        Generator yields:
            4-tuple of (url: str, filename: str, path: str, status: DownloadStatus)

        Args:
            download_dir (str): Directory to download files into. Gets created if it doesn't exist.
            timeout (float): Seconds to wait for the file to download. Defaults to 160.
            max_attempts (int): How many times to retry the download in case of failure. Defaults to 3.
            url_filter_re (str): Keep only URLs that match this regex. Defaults to r".+".
            filename_substitution_re_pat (str): Remove all charactes that match the regex. Defaults to r"".
            strip_prefix (bool): Strip the f-xxx-xxx-  or sig-xxx-xxx- prefix from filenames. Defaults to False.
            overwrite_existing (bool): Check download directory for files. If they already exist, don't download them. Defaults to True.
        """
        download_dir = Path(download_dir).resolve().as_posix()
        os.makedirs(download_dir, exist_ok=True)
        urls = self.extract_urls(url_filter_re)
        filtered_URLs = filter_urls(
            urls,
            download_dir,
            strip_prefix=strip_prefix,
            filename_substitution_re_pat=filename_substitution_re_pat,
            overwrite_existing=overwrite_existing,
        )
        # ----
        with Session() as session:
            for url, path in filtered_URLs:
                status = download_sync(
                    url,
                    path,
                    session,
                    timeout=timeout,
                    max_attempts=max_attempts,
                )
                yield status

    def async_downloader(
        self,
        download_dir: str,
        max_concurrent: int = 5,
        timeout: float = 160,
        max_attempts: int = 3,
        url_filter_re: str = r".+",
        filename_substitution_re_pat: str = r"",
        strip_prefix: bool = False,
        overwrite_existing: bool = True,
        callback: Optional[Callable] = None,
    ) -> AsyncFormDownloader:
        """Download files uploaded to the form via the File upload control (async)

        Returns a coroutine that runs the download process.

        Args:
            download_dir (str): Directory to download files into. Gets created if it doesn't exist.
            max_concurrent (int): Maximum concurrent downloads allowed. Defaults to 5.
            timeout (float): Seconds to wait for the file to download. Defaults to 160.
            max_attempts (int): How many times to retry the download in case of failure. Defaults to 3.
            url_filter_re (str): Keep only URLs that match this regex. Defaults to r".+".
            filename_substitution_re_pat (str): Remove all charactes that match the regex. Defaults to r"".
            strip_prefix (bool): Strip the f-xxx-xxx-  or sig-xxx-xxx- prefix from filenames. Defaults to False.
            overwrite_existing (bool): Check download directory for files. If they already exist, don't download them. Defaults to True.
            callback (Optional[Callable], optional): Callback called each time a download is complete. Defaults to None.
        """

        download_dir = Path(download_dir).resolve().as_posix()
        os.makedirs(download_dir, exist_ok=True)
        urls = self.extract_urls(url_filter_re)
        filtered_URLs = filter_urls(
            urls,
            download_dir,
            strip_prefix=strip_prefix,
            filename_substitution_re_pat=filename_substitution_re_pat,
            overwrite_existing=overwrite_existing,
        )
        # ----
        downloader = AsyncFormDownloader(
            download_dir,
            filtered_URLs,
            max_concurrent,
            timeout,
            max_attempts,
            callback,
        )
        # ----
        return downloader

    def extract_urls(self, filter_re_pat=r".+") -> List[str]:
        """Extract all URLs of files uploaded to the form

        Args:
            filter_re_pat (regexp, optional): Output only the URLs that match the input regex. Defaults to r".+".

        Returns:
            List[str]: List of URLs to files uploaded to the form.
        """
        url_re_pat = (
            rf"(https\:\/\/{self.server}\.formsite\.com\/{self.directory}\/files\/.*)"
        )
        url_re = re.compile(url_re_pat)
        urls = set()
        for col in self.data.columns:
            try:
                url_mask: pd.Index = self.data[col].str.fullmatch(url_re) == True
                tmp: pd.Series = self.data[url_mask][col]
                tmp = tmp.str.split("|")
                tmp = tmp.explode().str.strip()
                urls = urls.union(tmp.to_list())
            except AttributeError:
                pass

        # Return all URLs that match filter_re_pat
        filter_re = re.compile(filter_re_pat)
        return sorted([url for url in urls if filter_re.match(url)])
