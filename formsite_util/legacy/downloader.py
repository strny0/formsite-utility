"""
downloader.py

this module contains the functionality for downloading downloading
many urls concurrently with a worker queue+semaphore asyncio approach
"""
from __future__ import annotations
import os
import re
from pathlib import Path
import asyncio
import shutil
from time import perf_counter
from typing import Callable, Iterable, Optional, Set, Tuple
from dataclasses import dataclass
from tqdm import tqdm
from aiohttp import (
    ClientSession,
    ClientTimeout,
    TCPConnector,
    ClientResponseError,
    InvalidURL,
)


@dataclass
class _FormsiteDownloader:

    """Handles the distribution of downlaod tasks across DownloadWorkers."""

    download_folder: str
    links: Iterable[str]
    max_concurrent_downloads: int = 10
    timeout: int = 80
    retries: int = 1
    filename_regex: str = r""
    strip_prefix: bool = False
    overwrite_existing: bool = True
    report_downloads: bool = False
    write_failed: bool = True
    display_progress: bool = True

    def __post_init__(self):
        """Initializes internal variables."""
        self.filename_compiled_regex = re.compile(self.filename_regex)
        self.semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        self.dl_queue = asyncio.Queue()
        if not self.overwrite_existing and len(self.links) > 0:
            for element in self.links:
                url = element.rsplit("/", 1)[0] + "/"
                break
            filenames_in_dl_dir = self._list_files_in_download_dir(url)
            self.links = set(self.links) - filenames_in_dl_dir
        else:
            self.links = set(self.links)
        self.internal_state = DownloadWorkerState(
            self.links, self.max_concurrent_downloads
        )

    async def Start(self) -> None:
        """Starts download of links."""
        pbar = (
            tqdm(
                total=len(self.links),
                desc="Downloading files",
                unit="f",
                leave=False,
                dynamic_ncols=True,
                ncols=80,
            )
            if self.display_progress
            else None
        )
        os.makedirs(self.download_folder, exist_ok=True)
        async with ClientSession(connector=TCPConnector(limit=0)) as session:
            self.internal_state.update_pbar_callback = pbar.update if pbar else None
            for link in self.links:
                self.dl_queue.put_nowait((link, 0))
            tasks = [
                asyncio.ensure_future(
                    DownloadWorker(
                        self.download_folder,
                        self.dl_queue,
                        self.semaphore,
                        session,
                        self.internal_state,
                        timeout=self.timeout,
                        retries=self.retries,
                        pbar=pbar,
                        filename_regex=self.filename_regex,
                        strip_prefix=self.strip_prefix,
                    ).main()
                )
                for _ in range(self.max_concurrent_downloads)
            ]
            await asyncio.gather(*tasks)
        pbar.close() if pbar else None
        if self.internal_state.failed > 0 and self.write_failed:
            self.internal_state.write_failed()
        if self.report_downloads:
            self.internal_state.write_all()

    def _list_files_in_download_dir(self, url: str) -> Set[str]:
        """Lists all files in `self.download_folder`, inserts `url` before the filename."""
        filenames_in_dir = set()
        for file in os.listdir(self.download_folder):
            filenames_in_dir.add(url + file)
        return filenames_in_dir


@dataclass
class DownloadWorkerState:

    """Contains methods that track internal downlaod progressa cross downloader workers."""

    urls: Iterable[str]
    active_workers: int

    def __post_init__(self):
        self.urls = set(self.urls)
        self.total: int = len(self.urls)
        self.enqueued: int = len(self.urls)
        self.in_progress: int = 0
        self.success: int = 0
        self.failed: int = 0
        self.failed_urls: set = set()
        self.success_urls: set = set()
        self.complete_urls: list = list()
        self.update_pbar_callback: Optional[Callable] = None
        self.last_progress_display_update = 0

    def total_complete(self):
        """Returns sum of `self.success` and `self.failed`"""
        return self.success + self.failed

    def write_failed(self, target: str = "./failed_downloads.txt"):
        """Writes contents of `self.failed_urls` to a file."""
        with open(target, "a", encoding="utf-8") as writer:
            to_write = self.get_failed_url_diff()
            for i in to_write:
                writer.write(f"{i}\n")
        print(
            f"{len(to_write)} failures, please see failed_downloads.txt for more info"
            "\nfor timeout errors, try increasing timeout or reducing max concurrent downloads"
        )

    def write_all(self, target: str = "./downloads_status.txt"):
        """Writes contents of `self.complete_urls` to a file."""
        with open(target, "w", encoding="utf-8") as writer:
            for i in self.complete_urls:
                writer.write(f"{i}\n")

    def display_relevant_info(self):
        """Debug: prints some relevant internal state values"""
        print("----------------------------------")
        print(f"enqueued: {self.enqueued}")
        print(f"active workers: {self.active_workers}")
        print(f"files in progress: {self.in_progress}")
        print(f"success: {self.success}")
        print(f"failed: {self.failed}")

    def try_exit(self) -> bool:
        """Checks if it is possible to terminate worker."""
        if self.total_complete() >= self.total:
            return True
        elif self.enqueued > 0:
            return False
        elif self.active_workers > self.in_progress:
            return True
        else:
            return False

    def can_terminate_worker(self) -> bool:
        """Decrements allowed number of active workers if conditions allow it."""
        if self.try_exit():
            self.active_workers -= 1
            return True
        else:
            return False

    def mark_success(self, url: str) -> None:
        """Increments internal counter to match completed downloads."""
        self._mark(url, "OK", self.success_urls, self.success)

    def mark_fail(self, url: str, fail_exception: Exception) -> None:
        """Increments internal counter to match completed downloads."""
        self._mark(url, repr(fail_exception), self.failed_urls, self.failed)

    def _mark(self, url: str, status: str, add_to: Set[str], count_to: int):
        """Base method for changing internal state counts."""
        self.complete_urls.append(f"{url};\t{status}")
        add_to.add(f"{url}")
        count_to += 1
        if self.update_pbar_callback is not None:
            self.update_pbar_callback(1)

    def end_iteration(self) -> None:
        """Runs at the end of a download iteration."""
        self.in_progress -= 1

    def start_iteration(self) -> None:
        """Runs at the start of a download iteration."""
        self.enqueued -= 1
        self.in_progress += 1

    def get_failed_url_diff(self) -> Set[str]:
        """Returns a difference between all input URLs and successfully downloaded urls."""
        return set(self.urls) - set(self.success_urls)


@dataclass
class DownloadWorker:

    """download_folder is a path to download directory,
    \nqueue, semaphore, session, internal state and pbar are shared across all workers
    """

    download_folder: str
    queue: asyncio.Queue
    semaphore: asyncio.Semaphore
    session: ClientSession
    internal_state: DownloadWorkerState
    timeout: int = 80
    retries: int = 1
    pbar: tqdm = None
    filename_regex: str = r""
    strip_prefix: bool = False

    def __post_init__(self):
        self.client_timeout = ClientTimeout(total=self.timeout)
        self.filename_compiled_regex = re.compile(self.filename_regex)
        self.display_progress = None if self.pbar is None else True

    async def main(self) -> int:
        """Entrypoint for launching the download process."""
        while True:
            try:
                if self.internal_state.can_terminate_worker():
                    break
                url, attempt = await self.queue.get()
                await self.semaphore.acquire()
                if (
                    abs(self.internal_state.last_progress_display_update - perf_counter())
                    > 5
                ):  # seconds
                    self._update_pbar(desc="Downloading files")
                self.internal_state.start_iteration()
                try:
                    response = await self._download(url)
                    if response == 0:
                        self.internal_state.mark_success(url)
                except Exception as download_exception:
                    self._error_handling(download_exception, url, attempt)
            except asyncio.CancelledError:
                pass
            finally:
                self.semaphore.release()
                self.internal_state.end_iteration()
        return 0

    async def _fetch(
        self,
        url: str,
        filename: str,
        target: str,
        chunk_size: int = 4 * 1024,
        in_progress_ext: str = ".tmp",
    ) -> int:
        """The core download function with `session.get` request."""
        display_name = (
            filename[:20] + "…" + filename[-5:] if len(filename) > 25 else filename[:25]
        )
        async with self.session.get(url, timeout=self.client_timeout) as response:
            response.raise_for_status()
            pbar = (
                tqdm(
                    desc=display_name,
                    total=response.content_length,
                    leave=False,
                    unit="b",
                    unit_scale=True,
                    unit_divisor=1024,
                    ncols=80,
                )
                if self.display_progress
                else None
            )
            with open(target + in_progress_ext, "wb") as f:
                async for chunk in response.content.iter_chunked(chunk_size):
                    f.write(chunk)
                    pbar.update(len(chunk)) if pbar else None

        pbar.close() if pbar else None
        shutil.move(target + in_progress_ext, target)
        return 0

    async def _download(self, url: str) -> int:
        """Wrapper for starting the `self.fetch` operation."""
        filename, target = self.get_filename(url)
        exit_code = await self._fetch(url, filename, target)
        return exit_code

    def _error_handling(self, exception: Exception, url: str, attempt: int) -> None:
        """Decides what errors cancel downloads and which are retried."""
        if isinstance(exception, ClientResponseError):
            if exception.status == 403:
                self._update_pbar(desc=f"{exception}"[:79] + "…")
                self.internal_state.last_progress_display_update = perf_counter()
                self.internal_state.mark_fail(url, exception)
            elif exception.status == 404:
                self._update_pbar(desc=f"{exception}"[:79] + "…")
                self.internal_state.last_progress_display_update = perf_counter()
                self.internal_state.mark_fail(url, exception)
            else:
                self._retry_dl(url, attempt)
        elif isinstance(exception, InvalidURL):
            self.internal_state.mark_fail(url, exception)
        elif attempt < self.retries:
            self._retry_dl(url, attempt)
        else:
            self._update_pbar(desc=f"Failed {url}"[:79] + "…")
            self.internal_state.last_progress_display_update = perf_counter()
            self.internal_state.mark_fail(url, exception)

    def _retry_dl(self, url: str, attempt: int) -> None:
        """Puts failed downloads to the end of queue, if attempt < max retry."""
        self._update_pbar(
            desc=f"Retrying ({attempt}/{self.retries}) download of {url}"[:79] + "…"
        )
        self.internal_state.last_progress_display_update = perf_counter()
        attempt += 1
        self.internal_state.enqueued += 1
        self.queue.put_nowait((url, attempt))

    def _update_pbar(self, desc: str = ""):
        """Updates main download progress bar with a provided description."""
        if isinstance(self.pbar, tqdm):
            self.pbar.set_description(desc=desc, refresh=True)

    def get_filename(self, url: str) -> Tuple[str, str]:
        """Gets filename from url. Returns filename and path+filename as target."""
        filename = f"{url.split('/')[-1:][0]}"
        if self.strip_prefix:
            filename = re.sub(r"^f-[\d]*-[\d]*-", r"", filename)
        if self.filename_compiled_regex.pattern != "":
            filename = self._regex_substitution(filename, self.filename_compiled_regex)
            target = f"{self.download_folder}/{filename}"
            target = self._check_if_file_exists(target)
        else:
            target = f"{self.download_folder}/{filename}"
        return filename, target

    def _check_if_file_exists(self, filename: str, appended_number: int = 0) -> str:
        """If `overwrite_downloads is False`, checks which URLs to omit based on filenames."""
        path = Path(filename).resolve()
        if path.exists():
            temp = filename.rsplit(".", 1)
            if temp[0].endswith(f"_{appended_number}"):
                temp[0] = temp[0][: temp[0].rfind(f"_{appended_number}")]
            try:
                filename = temp[0] + f"_{appended_number+1}." + temp[1]
            except IndexError:
                filename = temp[0] + f"_{appended_number+1}"
            filename = self._check_if_file_exists(
                filename, appended_number=appended_number + 1
            )
        return filename

    def _regex_substitution(self, filename: str, filename_regex: re.Pattern) -> str:
        """Removes characters that match regex."""
        try:
            old_filename_tuple = filename.rsplit(".", 1)
            try:
                new_filename = f"{filename_regex.sub('', old_filename_tuple[0])}.{old_filename_tuple[1]}"
            except:
                new_filename = f"{filename_regex.sub('', old_filename_tuple[0])}"
        except:
            new_filename = f"{filename_regex.sub('', filename)}"
        return new_filename
