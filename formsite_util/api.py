"""
api.py

This module contains a class that handles API requests to Formsite API.
"""
from typing import Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
from tqdm.asyncio import tqdm
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientResponseError
from aiofiles import open as aiopen


@dataclass
class _FormsiteAPI:

    """Handles retreival of results from your formsite form. Invoked with `self.Start()` method.
    \nKeywords:
    \nResults: Data from your formsite form (the rows).
    \nItems:   Names of user-defined columns in your formsite form (the header row).
    \nInputs:
    \ninterface: instance of FormsiteInterface class from core.py
    \nsave_results_jsons: whether to write received results to json files
    \nsave_items_json: whether to write received itmes to json files"""
    interface: Any
    save_results_jsons: bool = False
    save_items_json: bool = False
    display_progress:bool = True

    def __post_init__(self):
        self.params_dict: dict = self.interface.params_dict
        self.items_dict: dict = self.interface.items_dict
        self.auth_dict: dict = self.interface.auth_dict
        self.form_id: str = self.interface.form_id
        self.results_url: str = f'{self.interface.url_base}/forms/{self.interface.form_id}/results'
        self.items_url: str = f'{self.interface.url_base}/forms/{self.interface.form_id}/items'
        self.total_pages: int = 1
        self.check_pages: bool = True

    async def Start(self, only_items: bool = False) -> Tuple[str, Optional[List[str]]]:
        """Performs all API calls to formsite servers asynchronously"""
        items, results = (None, [])
        async with ClientSession(headers=self.auth_dict, timeout=ClientTimeout(total=None), connector=TCPConnector(limit=None)) as self.session:
            self.pbar = tqdm(desc='Starting API requests', total=2, unit=' calls', leave=False) if self.display_progress else None
            if not only_items:
                self._update_pbar_desc(desc="Fetching results")
                results = [await self.fetch_results(self.params_dict, 1)]
                tasks = []
                if self.total_pages > 1:
                    for page in range(2, self.total_pages+1):
                        tasks.append(asyncio.ensure_future(self.fetch_results(self.params_dict, page)))
                completed_tasks = await asyncio.gather(*tasks)
                results += completed_tasks
                while None in results: results.remove(None)
            self._update_pbar_desc(desc="Fetching items")
            items: str = await self.fetch_items()
            self._update_pbar_progress()
            self._update_pbar_desc(desc="API calls complete")
            try:
                self.pbar.close()
            except AttributeError:
                pass
        return items, results

    async def fetch_results(self, params: dict, page: int) -> str:
        """Handles fetching and writing (if selected) of results json."""
        content = await self.fetch_content(self.results_url, params, page=page)
        if self.save_results_jsons:
            await self.write_content(f'./results_{self.form_id}_{page}.json', content)
        return content

    async def write_content(self, filename: str, content: str) -> None:
        """Handles writing of any string (json)."""
        async with aiopen(filename, 'wb') as writer:
            try:
                await writer.write(content)
            except TypeError:
                await writer.write(content.encode('utf-8'))

    async def fetch_content(self, url: str, params: dict, page: int = None) -> str:
        """Base method for interacting with the formsite api with aiohttp GET request. Returns content of the response."""
        if page is not None:
            params['page'] = page
        async with self.session.get(url, params=params) as response:
            content = await response.content.read()
            if response.status != 200:
                self._update_pbar_desc(desc=f"Error {response.status}")
                if response.status == 429:
                    self._update_pbar_desc(desc="Reached rate limit, waiting 60 seconds")
                    await asyncio.sleep(60)
                    self._update_pbar_desc(desc="Fetching items")
                    content = await self.fetch_content(url, params, page=page)
                else:
                    try:
                        response.raise_for_status()
                    except ClientResponseError as e_x:
                        #print(f" {response.status} | {content.decode('utf-8', errors='ignore')}")
                        raise e_x
            if self.check_pages:
                self.total_pages = int(response.headers['Pagination-Page-Last'])
                self.check_pages = False
                try:
                    self.pbar.total = self.total_pages
                except AttributeError:
                    pass
        self._update_pbar_progress()
        try:
            return content.decode('utf-8')
        except AttributeError:
            return content

    async def fetch_items(self) -> str:
        """Handles fetching and writing (if selected) of items json."""
        content = await self.fetch_content(self.items_url, self.items_dict)
        if self.save_items_json:
            await self.write_content(f'./items_{self.form_id}.json', content)
        return content

    def _update_pbar_progress(self) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.update(1)

    def _update_pbar_desc(self, desc: str) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.set_description(desc=desc, refresh=True)
