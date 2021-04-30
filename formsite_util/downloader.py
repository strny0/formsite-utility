from pathlib import Path
from typing import Iterable
from tqdm.asyncio import tqdm
import os
from regex import compile
import asyncio
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientResponseError, InvalidURL
from aiofiles import open as aiopen
from dataclasses import dataclass
import shutil

@dataclass
class _FormsiteDownloader:
    download_folder: str
    links: Iterable[str]
    max_concurrent_downloads: int = 10
    timeout: int = 80
    retries: int = 1
    overwrite_existing: bool = True
    report_downloads: bool = False
    filename_regex: str = r''

    def __post_init__(self):
        self.filename_regex = compile(self.filename_regex)
        self.semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        self.dl_queue = asyncio.Queue()
        self.Ctimeout = ClientTimeout(total=self.timeout)
        self.internal_state = WorkerStateTracker(self.links, self.max_concurrent_downloads)
        if self.overwrite_existing == False and len(self.links) > 0:
            url = list(self.links)[0].rsplit('/',1)[0]
            filenames_in_dl_dir = self._list_files_in_download_dir(url)
            self.links = set(self.links) - filenames_in_dl_dir

    async def Start(self):
        """Starts download of links."""
        async with ClientSession(connector=TCPConnector(limit=None)) as session:
            with tqdm(total=len(self.links), desc="Downloading files", unit='files', leave=False) as self.pbar:
                self.internal_state.update_pbar_callback = self.pbar.update
                [self.dl_queue.put_nowait((link, session, 0))
                 for link in self.links]
                tasks = [asyncio.ensure_future(self._worker(
                    self.dl_queue, self.semaphore)) for _ in range(self.max_concurrent_downloads)]
                await asyncio.gather(*tasks)
                #[task.cancel() for task in tasks]
                self.pbar.set_description(desc="Download complete", refresh=True)
        try: await session.close()
        except: pass
        if self.internal_state.failed > 0:
           self.internal_state.write_failed()
        if self.report_downloads == True:
            self.internal_state.write_all()


    def _error_handling(self, e: Exception, queue, attempt, url, session):
        if isinstance(e, ClientResponseError):
            if e.status == 403:
                self.internal_state.mark_fail(url, e)
            elif e.status == 404:
                self.internal_state.mark_fail(url, e)
            else:
                self._retry_dl(queue, url, session, attempt)
        elif isinstance(e, InvalidURL):
            self.internal_state.mark_fail(url, e)
        elif attempt < self.retries:
            self._retry_dl(queue, url, session, attempt)
        else:
            self.internal_state.mark_fail(url, e)

    def _retry_dl(self, queue: asyncio.Queue, url, session, attempt):
        attempt+=1
        self.internal_state.enqueued += 1
        queue.put_nowait((url, session, attempt))

    async def _worker(self, queue: asyncio.Queue, semaphore: asyncio.Semaphore):
        while True:
            #self.internal_state.display_relevant_info()
            if self.internal_state.can_terminate_worker():
                self.internal_state.active_workers -= 1
                break
            url, session, attempt = await queue.get()
            await semaphore.acquire()
            self.internal_state.start_iteration()
            try:
                r = await self._download(url, session)
                if r == 0:
                    self.internal_state.mark_success(url)
            except Exception as e:
                self.pbar.set_description_str(desc=f"{repr(e)}", refresh=True)
                self._error_handling(e, queue, attempt, url, session)
                self.pbar.set_description(desc=f"Downloading files", refresh=True)
            finally:
                queue.task_done()
                semaphore.release()
                self.internal_state.end_iteration()
        return 0

    def _list_files_in_download_dir(self, url: str) -> set:
        filenames_in_dir = set()
        for file in os.listdir(self.download_folder):
            filenames_in_dir.add(url+file)
        return filenames_in_dir

    async def _fetch(self, url: str, session: ClientSession, filename:str, target:str, chunk_size:int = 4*1024, in_progress_ext='.tmp'):
        async with session.get(url, timeout=self.Ctimeout) as response:
            #print(f" {response.status} | downloading {url}")
            response.raise_for_status()
            with tqdm(desc=filename[:25]+"…", total=response.content_length, leave=False, unit='b', unit_scale=True, unit_divisor=1024, ncols=80) as pbar:
                async with aiopen(target+in_progress_ext, "wb") as writer:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        await writer.write(chunk)
                        pbar.update(len(chunk))
            shutil.move(target+in_progress_ext, target)
        return 0

    async def _download(self, url: str, session: ClientSession):
        filename, target = self.get_filename(url)
        exit_code = await self._fetch(url, session,filename, target)
        return exit_code

    def get_filename(self, url):
        filename = f"{url.split('/')[-1:][0]}"
        if self.filename_regex.pattern != '':
            filename = self._regex_substitution(filename, self.filename_regex)
            target = f"{self.download_folder}/{filename}"
            target = self._check_if_file_exists(target)
        else:
            target = f"{self.download_folder}/{filename}"
        return filename, target

    def _check_if_file_exists(self, filename, n=0) -> str:
        path = Path(filename).resolve()
        if path.exists():
            temp = filename.rsplit('.', 1)
            if temp[0].endswith(f'_{n}'):
                temp[0] = temp[0][:temp[0].rfind(f'_{n}')]
            try:
                filename = temp[0] + f"_{n+1}." + temp[1]
            except IndexError:
                filename = temp[0] + f"_{n+1}"
            filename = self._check_if_file_exists(filename, n=n+1)
        return filename

    def _regex_substitution(self, filename, filename_regex):
        try:
            temp = filename.rsplit('.', 1)
            try:
                filename = f"{filename_regex.sub('', temp[0])}.{temp[1]}"
            except:
                filename = f"{filename_regex.sub('', temp[0])}"
        except:
            filename = f"{filename_regex.sub('', filename)}"
        return filename

@dataclass
class WorkerStateTracker:
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
        self.update_pbar_callback = None


    def total_complete(self):
        return self.success + self.failed

    def write_failed(self):
        with open('./failed_downloads.txt', 'a') as writer:
            to_write = self.get_failed_url_diff()
            for i in to_write:
                writer.write(f"{i}\n")
        print(f"{len(to_write)} files failed to download, please see failed_downloads.txt for more info\nif the error is not 403, try increasing timeout or reducing max concurrent downloads")

    def write_all(self):
        with open('./downloads_status.txt', 'w') as writer:
            for i in self.complete_urls:
                writer.write(f"{i}\n")

    def display_relevant_info(self):
        print('----------------------------------')
        print(f"enqueued: {self.enqueued}")
        print(f"active workers: {self.active_workers}")
        print(f"files in progress: {self.in_progress}")
        print(f"success: {self.success}")
        print(f"failed: {self.failed}")
    
    def try_exit(self) -> bool:
        if self.total_complete() >= self.total:
            return True
        elif self.enqueued > 0:
            return False
        elif self.active_workers > self.in_progress:
            return True
        else: return False

    def can_terminate_worker(self):
        if self.try_exit():
            return True

    def mark_success(self, url: str):
        self.complete_urls.append(f"{url} ;   OK")
        self.success_urls.add(f"{url}")
        self.success += 1
        self.update_pbar_callback(1)

    def mark_fail(self, url: str, e: Exception):
        self.complete_urls.append(f"{url} ;   {repr(e)}")
        self.failed_urls.add(f"{url}")
        self.failed += 1
        self.update_pbar_callback(1)

    def end_iteration(self):
        self.in_progress -= 1

    def start_iteration(self):
        self.enqueued -= 1
        self.in_progress += 1
    
    def get_failed_url_diff(self):
        return self.urls - self.success_urls
