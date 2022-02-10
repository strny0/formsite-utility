"""

form.py

"""

from __future__ import annotations
from math import ceil
import os
from pathlib import Path
from time import sleep
import re
from typing import Callable, Coroutine, Generator, List, Optional
import pandas as pd
from requests import Session

# ----
from formsite_util.form_error import FormsiteNoResultsException
from formsite_util.logger import FormsiteLogger
from formsite_util.parameters import FormsiteParameters
from formsite_util.session import FormsiteSession
from formsite_util.fetcher import FormFetcher
from formsite_util.form_parser import FormParser
from formsite_util.download import download_sync, filter_urls
from formsite_util.download_async import AsyncFormDownloader
from formsite_util.form_data import FormData


def tz_shif_inplace(df: pd.DataFrame, col: str, tz_name: str):
    """Converts a tz-aware dataframe column to target timezone"""
    if col in df:
        df[col] = df[col].dt.tz_convert(tz=tz_name)


class FormsiteForm(FormData):
    """Formsite API Form object, representing the data and HTTP session"""

    def __init__(
        self,
        form_id: str = None,
        session: FormsiteSession = None,
        token: str = None,
        server: str = None,
        directory: str = None,
        data: FormData = None,
    ):
        """FormsiteForm master constructor

        Args:
            form_id (str): Formsite Form ID
            session (FormsiteSession): FormsiteSession object
            data (FormData, optional): Prepopulate form with this FormData object

            OR

            form_id (str): Formsite Form ID
            token (str): Formsite API Token
            server (str): Formsite Server (fsX.formsite.com)
            directory (str): Formsite Directory
            data (FormData, optional): Prepopulate form with this FormData object
        """

        super().__init__()
        self.form_id: str = form_id
        self.session: FormsiteSession = session

        if (
            session is None
            and token is not None
            and server is not None
            and directory is not None
        ):
            self.session = FormsiteSession(token, server, directory)

        if data is not None:
            self._data = data._data
            self._items = data._items
            self._uses_items = data._uses_items

        self.logger.debug(f"FormsiteForm: Initialized form object {form_id}")

    def __repr__(self) -> str:
        return f"<FormsiteForm {self.form_id}>"

    @classmethod
    def from_credentials(
        cls,
        form_id: str,
        token: str,
        server: str,
        directory: str,
        data: Optional[FormData] = None,
    ) -> FormsiteForm:
        """FormsiteForm constructor

        Args:
            form_id (str): Formsite Form ID
            token (str): Formsite API Token
            server (str): Formsite Server (fsX.formsite.com)
            directory (str): Formsite User directory
            data (FormData, optional): Prepopulate form with this FormData object
        """
        session = FormsiteSession(token, server, directory)
        return cls(form_id=form_id, session=session, data=data)

    @classmethod
    def from_session(
        cls,
        form_id: str,
        session: FormsiteSession,
        data: Optional[FormData] = None,
    ) -> FormsiteForm:
        """FormsiteForm constructor (share same HTTP session across different forms)

        Args:
            form_id (str): Formsite Form ID
            session (FormsiteSession): FormsiteSession object
            data (FormData, optional): Prepopulate form with this FormData object

        Returns:
            FormsiteForm: FormsiteForm object
        """
        return cls(form_id=form_id, session=session, data=data)

    def fetch(
        self,
        results: bool = True,
        items: bool = True,
        use_items: bool = True,
        params: FormsiteParameters = FormsiteParameters(),
        fetch_delay: float = 3.0,
        fetch_callback: Callable = None,
    ):
        """Updates the FormsiteForm object instance with the data from Formsite accoridng to input

        Args:
            results (bool, optional): Pull results within parameters. Defaults to True.
            items (bool, optional): Pull items (of resultslabels id). Defaults to True.
            use_items (bool, optional): Set columns to use labels from items, otherwise use column ids and metadata ids. Defaults to True.
            params (FormsiteParameters): Pull results and items according to these parameters.
            fetch_delay (float): Time delay between individual API calls in seconds.
            fetch_callback (Callable, optional): Run this callback every time an API fetch is complete.

        fetch_callback function signature:
            function(cur_page: int, total_pages: int, data: dict) -> None
        """
        assert self.session is not None, "Initialized without FormsiteSession object."
        fetcher = FormFetcher(self.form_id, self.session, params)
        parser = FormParser()
        self.uses_items = False
        msg = f"Formsite Form: Fetching data for {self.form_id} | {params}"
        self.logger.debug(msg)
        if results:
            for data in fetcher.fetch_iterator():
                # --- edge case ---
                if not data.get("results"):
                    raise FormsiteNoResultsException("No results in specified parameters")
                # --- regular case ---
                parser.feed(data)
                # --- callback ---
                if isinstance(fetch_callback, Callable):
                    fetch_callback(fetcher.cur_page, fetcher.total_pages, data)
                # --- fetch delay ---
                sleep(fetch_delay)

            self.data = parser.as_dataframe()
            tz_shif_inplace(self.data, "date_update", params.timezone)
            tz_shif_inplace(self.data, "date_start", params.timezone)
            tz_shif_inplace(self.data, "date_finish", params.timezone)
            if params.last is not None:
                self.data = self.data.head(params.last)

        if items:
            self.items = fetcher.fetch_items()
            if use_items:
                self.uses_items = True
                rename_map = parser.create_rename_map(self.items)
                self.data = self.data.rename(columns=rename_map)

    def downloader(
        self,
        download_dir: str,
        timeout: float = 160,
        max_attempts: int = 3,
        url_filter_re: str = r".+",
        filename_substitution_re_pat: str = r"",
        strip_prefix: bool = False,
        overwrite_existing: bool = True,
    ) -> Generator[int, None, None]:
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
        url_re_pat = rf"(https\:\/\/{self.session.server}\.formsite\.com\/{self.session.directory}\/files\/.*)"
        url_re = re.compile(url_re_pat)
        urls = set()
        for col in self.data.columns:
            try:
                tmp = self.data[self.data[col].str.fullmatch(url_re) == True][col]
                tmp = tmp.str.split("|")
                tmp = tmp.explode().str.strip()
                urls = urls.union(tmp.to_list())
            except AttributeError:
                pass

        # Return all URLs that match filter_re_pat
        filter_re = re.compile(filter_re_pat)
        return sorted([url for url in urls if filter_re.match(url)])
