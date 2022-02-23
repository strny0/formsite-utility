"""This module contains the functionality for downloading downloading many urls concurrently with a worker based queue+semaphore asyncio approach."""

from __future__ import annotations
import os
from collections import namedtuple
import asyncio
import shutil
from typing import Callable, List, Optional, Set
from aiohttp import (
    ClientSession,
    ClientTimeout,
    TCPConnector,
    ClientResponseError,
    InvalidURL,
)

from formsite_util.logger import FormsiteLogger

DownloadItem = namedtuple("DownloadItem", ["url", "path", "attempt"])


class AsyncFormDownloader:

    """Handles the distribution of downlaod tasks across DownloadWorkers."""

    def __init__(
        self,
        download_dir: str,
        sorted_urls: List[str, str],
        workers: int = 5,
        timeout: int = 160,
        max_attempts: int = 1,
        callback: Optional[Callable] = None,
    ) -> None:
        """AsyncFormDownloader constructor

        Args:
            download_dir (str)
            sorted_urls (List[str, str]): List of (url, path)
            workers (int, optional): Number of concurrent downloads. Defaults to 5.
            timeout (int, optional): Download timeout. Defaults to 160.
            max_attempts (int, optional): Max number of attempts. Defaults to 1.
            callback (Optional[Callable], optional): Callback called each time a download is complete. Defaults to None.

        Callback function signature:
            (url: str, path: str, total_files: int) -> None
        """
        # ----
        self.download_dir = download_dir
        self.url_path_list = sorted_urls
        self.workers = workers
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.logger: FormsiteLogger = FormsiteLogger()
        # ----
        self.semaphore = asyncio.Semaphore(self.workers)
        self.dl_queue = asyncio.Queue()
        self.internal_state = DownloadWorkerState(
            self.url_path_list,
            self.workers,
            callback=callback,
        )

    async def run(self) -> None:
        """Entrypoint"""
        os.makedirs(self.download_dir, exist_ok=True)
        async with ClientSession(connector=TCPConnector(limit=0)) as session:
            for url, path in self.url_path_list:
                dl = DownloadItem(url, path, 0)
                self.dl_queue.put_nowait(dl)
            tasks = [
                asyncio.ensure_future(
                    DownloadWorker(
                        self.download_dir,
                        self.dl_queue,
                        self.semaphore,
                        session,
                        self.internal_state,
                        timeout=self.timeout,
                        max_attempts=self.max_attempts,
                    ).run()
                )
                for _ in range(self.workers)
            ]

            await asyncio.gather(*tasks)


class DownloadWorkerState:
    """Contains methods that track internal downlaod progress across downloader workers."""

    def __init__(
        self,
        url_path_list: List[str, str],
        num_workers: int,
        callback: Optional[Callable] = None,
    ) -> None:
        self.url_path_list = url_path_list
        self.num_workers = num_workers
        self.callback = callback
        self.logger: FormsiteLogger = FormsiteLogger()
        # ----
        self.total: int = len(self.url_path_list)
        self.enqueued: int = len(self.url_path_list)
        self.in_progress: int = 0
        self.success: int = 0
        self.failed: int = 0
        self.failed_urls: set = set()
        self.success_urls: set = set()
        self.complete_urls: list = []

    def total_complete(self):
        """Returns sum of `self.success` and `self.failed`"""
        return self.success + self.failed

    def try_exit(self) -> bool:
        """Checks if it is possible to terminate worker."""
        if self.total_complete() >= self.total:
            return True
        elif self.enqueued < self.num_workers:
            return True
        else:
            return False

    def can_terminate_worker(self) -> bool:
        """Decrements allowed number of active workers if conditions allow it."""
        if self.try_exit():
            self.num_workers -= 1
            return True
        else:
            return False

    def mark_success(self, dl: DownloadItem) -> None:
        """Increments internal counter to match completed downloads."""
        self.logger.debug(f"DownloadStatus: Success '{dl.url}' saved in '{dl.path}'")
        self._mark(dl, "OK", self.success_urls, self.success)

    def mark_fail(self, dl: DownloadItem, fail_exception: Exception) -> None:
        """Increments internal counter to match completed downloads."""
        self.logger.debug(f"DownloadStatus: Failure '{dl.url}'")
        self._mark(dl, repr(fail_exception), self.failed_urls, self.failed)

    def _mark(self, dl: DownloadItem, status: str, add_to: Set[str], count_to: int):
        """Base method for changing internal state counts."""
        self.complete_urls.append(f"{dl.url} {status}")
        add_to.add(f"{dl.url}")
        count_to += 1

    def end_iteration(self) -> None:
        """Runs at the end of a download iteration."""
        self.in_progress -= 1

    def start_iteration(self) -> None:
        """Runs at the start of a download iteration."""
        self.enqueued -= 1
        self.in_progress += 1


class DownloadWorker:
    """download_folder is a path to download directory
    queue, semaphore, session, internal state and pbar are shared across all workers"""

    def __init__(
        self,
        download_folder: str,
        queue: asyncio.Queue,
        semaphore: asyncio.Semaphore,
        session: ClientSession,
        internal_state: DownloadWorkerState,
        timeout: int = 160,
        max_attempts: int = 3,
    ) -> None:
        # ----
        self.download_folder = download_folder
        self.queue = queue
        self.semaphore = semaphore
        self.session = session
        self.internal_state = internal_state
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.logger: FormsiteLogger = FormsiteLogger()
        # ----
        self.callback = internal_state.callback
        self.client_timeout = ClientTimeout(total=timeout)

    async def run(self) -> int:
        """Entrypoint for launching the download process."""
        while True:
            try:
                if self.internal_state.can_terminate_worker():
                    break
                await self.semaphore.acquire()
                dl: DownloadItem = await self.queue.get()
                self.internal_state.start_iteration()
                try:
                    await self._fetch(dl.url, dl.path)
                    self.internal_state.mark_success(dl)
                except Exception as download_exception:
                    self._error_handling(download_exception, dl)
            except asyncio.CancelledError:
                pass
            finally:
                self.semaphore.release()
                self.internal_state.end_iteration()

    async def _fetch(
        self,
        url: str,
        path: str,
        chunk_size: int = 4 * 1024,
    ) -> bool:
        """The core download function with `session.get` request."""
        async with self.session.get(url, timeout=self.client_timeout) as response:
            response.raise_for_status()
            with open(f"{path}.tmp", "wb") as f:
                async for chunk in response.content.iter_chunked(chunk_size):
                    f.write(chunk)

        shutil.move(f"{path}.tmp", path)
        if self.callback is not None:
            self.callback(url, path, self.internal_state.total)

    def _error_handling(self, ex: Exception, dl: DownloadItem) -> None:
        """Decides what errors cancel downloads and which are retried."""
        self.logger.debug(f"DownloadError: for '{dl.url}' | {ex}")
        if isinstance(ex, ClientResponseError):
            if ex.status in [403, 404]:
                self.internal_state.mark_fail(dl, ex)
            else:
                self._retry_dl(dl)
        elif isinstance(ex, InvalidURL):
            self.internal_state.mark_fail(dl, ex)
        elif dl.attempt < self.max_attempts:
            self._retry_dl(dl)
        else:
            self.internal_state.mark_fail(dl, ex)

    def _retry_dl(self, dl: DownloadItem) -> None:
        """Puts failed downloads to the end of queue, if attempt < max retry."""
        new_dl = DownloadItem(dl.url, dl.path, dl.attempt + 1)
        self.internal_state.enqueued += 1
        self.logger.debug(f"DownloadStatus: Retry '{dl.url}' attempt {dl.attempt}")
        self.queue.put_nowait(new_dl)
