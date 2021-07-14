"""
api.py

This module contains a class that handles API requests to Formsite API.
"""
from __future__ import annotations
import os
import json
from typing import List, Tuple, Any
from dataclasses import dataclass
import time
from pathlib import Path
import shutil
import requests
from requests.models import HTTPError
from tqdm import tqdm

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
    delay: float = 5.0
    long_delay: float = 15.0

    def __post_init__(self):
        """Generates post_init internal variables."""
        self.params_dict: dict = self.interface.params_dict
        self.items_dict: dict = self.interface.items_dict
        self.auth_dict: dict = self.interface.auth_dict
        self.form_id: str = self.interface.form_id
        self.results_url: str = f'{self.interface.url_base}/forms/{self.interface.form_id}/results'
        self.items_url: str = f'{self.interface.url_base}/forms/{self.interface.form_id}/items'
        self.total_pages: int = 1
        self.check_pages: bool = True
        self.pbar = None
        self.session = None
        self.save_results_jsons = Path(f'./{self.form_id}_tmp_results/').resolve().absolute().as_posix()
        self.save_items_json = Path(f'./{self.form_id}_tmp_items/').resolve().absolute().as_posix()
        os.makedirs(self.save_results_jsons, exist_ok=True)
        os.makedirs(self.save_items_json, exist_ok=True)

    def Start(self, only_items: bool = False) -> Tuple[dict, List[dict]]:
        """Performs all API calls to formsite servers asynchronously"""
        items, results = (None, [])
        with requests.session() as self.session:
            self.session.headers = self.auth_dict
            self.pbar = tqdm(desc='Starting API requests', total=2, unit=' calls', leave=False) if self.display_progress else None
            if not only_items:
                self._update_pbar_desc(desc="Fetching results")
                results = [self.fetch_results(self.params_dict, 1)]
                if self.total_pages > 1:
                    for page in range(2, self.total_pages+1):
                        results.append(self.fetch_results(self.params_dict, page))
                        if (page * 500) >= self.interface.params.last and isinstance(self.interface.params.last, int):
                            break
                        
            self._update_pbar_desc(desc="Fetching items")
            items = self.fetch_items()
            self._update_pbar_progress()
            self._update_pbar_desc(desc="API calls complete")
            try:
                self.pbar.close()
            except AttributeError:
                pass
        shutil.rmtree(path=self.save_results_jsons, ignore_errors=True)
        shutil.rmtree(path=self.save_items_json, ignore_errors=True)
        return items, results
    
    def check_existing_data(self):
        present_ref_ranges = []
        for f in os.listdir(self.save_results_jsons):
            if self.form_id in f:
                min_ref = int(f.split('_')[-2])
                max_ref = int(f.split('_')[-1])
                present_ref_ranges.append((min_ref, max_ref))
                
        return sorted(present_ref_ranges)
                
    def fetch_results(self, params: dict, page: int) -> str:
        """Handles fetching and writing (if selected) of results json."""
        content = self.fetch_content(self.results_url, params, page=page)
        max_ref = content['results'][0]['id']
        min_ref = content['results'][-1]['id']
        self.write_content(f'{self.save_results_jsons}/results_{self.form_id}_{min_ref}_{max_ref}.json', content)
        return content

    def write_content(self, filename: str, content: dict) -> None:
        """Handles writing of any string (json)."""
        with open(filename, 'w') as writer:
            json.dump(content, writer)

    def fetch_content(self, url: str, params: dict, page: int = None) -> dict:
        """Base method for interacting with the formsite api with aiohttp GET request. Returns content of the response."""
        if page is not None:
            params['page'] = page
            _ = time.sleep(abs(self.long_delay-self.delay)) if page > 3 else None
        time.sleep(self.delay)
        with self.session.get(url, params=params) as response:
            content = response.json()
            if response.status_code != 200:
                self._update_pbar_desc(desc=f"Error: [{response.status_code}]")
                if response.status == 429:
                    self._update_pbar_desc(desc="Reached rate limit, waiting 60 seconds")
                    time.sleep(60)
                    self._update_pbar_desc(desc="Fetching results")
                    content = self.fetch_content(url, params, page=page)
                else:
                    response.raise_for_status()
                    raise HTTPError(f"\r[{response.status_code}] {response.content}")
            if self.check_pages:
                self.total_pages = int(response.headers['Pagination-Page-Last'])
                self.check_pages = False
                try:
                    self.pbar.total = self.total_pages
                except AttributeError:
                    pass
        self._update_pbar_progress()
        return content


    def fetch_items(self) -> str:
        """Handles fetching and writing (if selected) of items json."""
        content = self.fetch_content(self.items_url, self.items_dict)
        self.write_content(f'{self.save_items_json}/items_{self.form_id}.json', content)
        return content

    def _update_pbar_progress(self) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.update(1)

    def _update_pbar_desc(self, desc: str) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.set_description(desc=desc, refresh=True)
