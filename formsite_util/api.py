from typing import Any
from tqdm.asyncio import tqdm
import asyncio
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientResponseError
from aiofiles import open as aiopen
from dataclasses import dataclass

@dataclass
class _FormsiteAPI:
    interface: Any
    save_results_jsons: bool = False
    save_items_json: bool = False
    refresh_items_json: bool = False

    def __post_init__(self):
        self.paramsHeader = self.interface.paramsHeader
        self.itemsHeader = self.interface.itemsHeader
        self.authHeader = self.interface.authHeader
        self.form_id = self.interface.form_id
        self.results_url = f'{self.interface.url_base}/forms/{self.interface.form_id}/results'
        self.items_url = f'{self.interface.url_base}/forms/{self.interface.form_id}/items'
        self._set_start_state()

    def _set_start_state(self):
        self.total_pages = 1
        self.check_pages = True

    async def Start(self, only_items=False):
        """Performs all API calls to formsite servers asynchronously"""
        async with ClientSession(headers=self.authHeader, timeout=ClientTimeout(total=None), connector=TCPConnector(limit=None)) as self.session:
            with tqdm(desc='Starting API requests', total=2, unit=' calls', leave=False) as self.pbar:
                if only_items:
                    items = await self.fetch_items()
                    self.pbar.update(1)
                    return items
                else:
                    self.pbar.set_description("Fetching results")
                    results = [await self.fetch_results(self.paramsHeader, 1)]
                    tasks = []
                    if self.total_pages > 1:
                        self.pbar.total = self.total_pages
                        for page in range(2,self.total_pages+1):
                            tasks.append(asyncio.ensure_future(self.fetch_results(self.paramsHeader, page)))
                    completed_tasks = await asyncio.gather(*tasks)
                    results += completed_tasks
                    self.pbar.set_description("Fetching items")
                    items = await self.fetch_items()
                    self.pbar.set_description("API calls complete")
        results.remove(None) if None in results else 0
        return items, results

    async def fetch_results(self, params:dict, page:int) -> str:
        content = await self.fetch_content(self.results_url, params, page=page)
        if self.save_results_jsons:
            await self.write_content(f'./results_{self.form_id}_{page}.json', content)
        self.pbar.update(1)
        return content

    async def write_content(self, filename, content) -> None:
        async with aiopen(filename, 'wb') as writer:
            try:
                await writer.write(content)
            except TypeError:
                await writer.write(content.encode('utf-8'))

    async def fetch_content(self, url, params, page=None) -> bytes:
        if page is not None:
            params['page'] = page
        async with self.session.get(url, params=params) as response:
            content = await response.content.read()
            if response.status != 200:
                self.pbar.set_description(f"Error {response.status}")
                if response.status == 429:
                    self.pbar.set_description("Reached rate limit, waiting 60 seconds")
                    await asyncio.sleep(60)
                    self.pbar.set_description("Fetching items")
                    content = await self.fetch_content(url, params, page=page)
                else:
                    try:
                        response.raise_for_status()
                    except ClientResponseError as e:
                        print(f" {response.status} | {content.decode('utf-8', errors='ignore')}")
                        raise e
            if self.check_pages == True:
                self.total_pages = int(response.headers['Pagination-Page-Last'])
                self.check_pages = False
        try:
            return content.decode('utf-8')
        except AttributeError:
            return content

    async def fetch_items(self) -> str:
        content = await self.fetch_content(self.items_url, self.itemsHeader)
        if self.save_items_json:
            await self.write_content(f'./items_{self.form_id}.json', content)
        self.pbar.update(1)
        return content

