#!/usr/bin/env python3
# Script: formsite_api.py
# Author: Jakub Strnad
# Description: https://github.com/strny0/formsite-utility
# Notes:    items - headers of the exported CSV, more specifically the part of the formsite export created by user (user controls)
#			results - rows of the exported CSV
#           Rate limits - formsite API allows max 2000 calls total per day or max 50 per minute, API calls will wait every time they fail for this reason (code 429)

from datetime import datetime as dt  # s
from datetime import timedelta as td  # s
from pathlib import Path as Path  # s
import json  # s
import concurrent.futures
from multiprocessing import cpu_count
from aiohttp.typedefs import PathLike

from tqdm.asyncio import tqdm  # !
import sys
import pytz  # !
import regex  # !
import asyncio  # !
from aiohttp import ClientSession, ClientTimeout, TCPConnector, request
import aiofiles
import pandas as pd  # !
import openpyxl  # !
import argparse  # !

class FormsiteParams:

    def __init__(self,
                 afterref=0,
                 beforeref=0,
                 afterdate="",
                 beforedate="",
                 resultslabels=10,
                 resultsview=11,
                 timezone='local',
                 date_format="",
                 sort="desc"):

        self.afterref = afterref
        self.beforeref = beforeref
        self.afterdate = afterdate
        self.beforedate = beforedate
        self.resultslabels = resultslabels
        self.resultsview = resultsview
        self.sort = sort
        self.timezone_offset, self.local_datetime = self._calculate_tz_offset(
            timezone)
        self.date_format = date_format
        self.colID_sort = 0  # which column it sorts by
        self.colID_equals = 0  # which column it looks into with equals search param
        self.colID_contains = 0  # which column it looks into with contains search param
        self.colID_begins = 0  # which column it looks into with begins search param
        self.colID_ends = 0  # which column it looks into with ends search param
        self.paramSearch_equals = ''
        self.paramSearch_contains = ''
        self.paramSearch_begins = ''
        self.paramSearch_ends = ''
        self.paramSearch_method = ''

    def getParamsHeader(self, single_page_limit=500) -> dict:  # 500 = max allowed size
        # Results header creation
        resultsParams = dict()
        resultsParams['page'] = 1
        resultsParams['limit'] = single_page_limit
        if self.afterref != 0:
            resultsParams['after_id'] = self.afterref
        if self.beforeref != 0:
            resultsParams['before_id'] = self.beforeref
        if self.afterdate != "":
            self.afterdate = self.__shift_param_date__(
                self.afterdate, self.timezone_offset)
            resultsParams['after_date'] = self.afterdate
        if self.beforedate != "":
            self.beforedate = self.__shift_param_date__(
                self.beforedate, self.timezone_offset)
            resultsParams['before_date'] = self.beforedate
        # 11 = all items + statistics
        resultsParams['results_view'] = self.resultsview
        if self.colID_sort != 0:
            resultsParams['sort_id'] = self.colID_sort
        if self.colID_equals != 0 or self.paramSearch_equals != '':
            resultsParams[f'search_equals[{self.colID_equals}] ='] = self.paramSearch_equals
        if self.colID_contains != 0 or self.paramSearch_contains != '':
            resultsParams[f'search_contains[{self.colID_contains}] ='] = self.paramSearch_contains
        if self.colID_begins != 0 or self.paramSearch_begins != '':
            resultsParams[f'search_begins[{self.colID_begins}] ='] = self.paramSearch_begins
        if self.colID_ends != 0 or self.paramSearch_ends != '':
            resultsParams[f'search_ends[{self.colID_ends}] ='] = self.paramSearch_ends
        if self.paramSearch_method != '':
            resultsParams['search_method'] = self.paramSearch_method
        return resultsParams

    def __shift_param_date__(self, date, timezone_offset) -> str:
        try:
            date = date - timezone_offset
        except:
            try:
                date = dt.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
                date = date - timezone_offset
            except:
                try:
                    date = dt.strptime(date, "%Y-%m-%d")
                    date = date - timezone_offset
                except:
                    try:
                        date = dt.strptime(date, "%Y-%m-%d %H:%M:%S")
                        date = date - timezone_offset
                    except:
                        raise Exception(
                            'invalid date format input for afterdate/beforedate, please use ISO 8601, yyyy-mm-dd or yyyy-mm-dd HH:MM:SS')
        date = dt.strftime(date, "%Y-%m-%dT%H:%M:%SZ")
        return date

    def _calculate_tz_offset(self, timezone):
        """Converts input timezone (offset from utc or tz databse name) to an offset relative to local timezone."""
        local_date = dt.now()
        if regex.search(r'(\+|\-|)([01]?\d|2[0-3])([0-5]\d)', timezone) is not None:
            inp = timezone.replace("'", "")
            inp = [inp[:2], inp[2:]] if len(inp) == 4 else [inp[:3], inp[3:]]
            offset_from_local = td(hours=int(inp[0]), seconds=int(inp[1])/60)
        elif regex.search(r'(\+|\-|)([01]?\d|2[0-3]):([0-5]\d)', timezone) is not None:
            inp = timezone.replace("'", "")
            inp = [inp[:2], inp[3:]] if len(inp) == 5 else [inp[:3], inp[4:]]
            offset_from_local = td(hours=int(inp[0]), seconds=int(inp[1])/60)
        elif regex.search(r'.+/.+', timezone) is not None:
            try:
                inp = pytz.timezone(timezone).localize(
                    local_date).strftime("%z")
                inp = [inp[:2], inp[2:]] if len(inp) == 4 else [
                    inp[:3], inp[3:]]
                offset_from_local = td(
                    hours=int(inp[0]), seconds=int(inp[1])/60)
            except:
                raise Exception("Invalid timezone format provided")
        elif timezone == 'local':
            offset_from_local = td(seconds=0)
        else:
            raise Exception("Invalid timezone format provided")

        return offset_from_local, local_date

    def getItemsHeader(self) -> dict:
        return {"results_labels": self.resultslabels}

class FormsiteCredentials:
    def __init__(self, username: str, api_token: str, fs_server: str, fs_directory: str):
        """Class which represents your user credentials for accessing the formsite API."""
        self.username = username
        self.token = api_token
        self.server = fs_server
        self.directory = fs_directory
        self.confirm_validity()

    def getAuthHeader(self) -> dict:
        """Returns a dictionary sent as a header in the API request for authorization purposes."""
        return {"Authorization": f"{self.username} {self.token}", "Accept": "application/json"}

    def confirm_validity(self):
        """Checks if credentials input is in correct format."""
        self.username = self._confirm_arg_format(
            self.username, 'username', '-u', 'username')
        self.token = self._confirm_arg_format(
            self.token, 'token', '-t', 'token')
        self.server = self._confirm_arg_format(
            self.server, 'server', '-s', 'fs1')
        self.directory = self._confirm_arg_format(
            self.directory, 'directory', '-d', 'Wa37fh')

    def _confirm_arg_format(self, argument, argument_name, flag, example) -> str:
        """Validates input from `cli`."""
        quotes_map = [('\'', ''), ('\"', '')]
        if type(argument) != str:
            raise Exception(
                f'invalid format for argument {argument}, {argument_name}, correct example: {example}')
        argument = self._sanitize_argument(argument, quotes_map)
        return argument

    def _sanitize_argument(self, argument, chars2remove) -> str:
        """Sanitizes input from `cli`."""
        for k, v in chars2remove:
            argument = str(argument).replace(k, v)
        return argument

class FormsiteInterface:

    def __init__(self, form_id: str, login: FormsiteCredentials, formsite_params=FormsiteParams(), verbose=False):
        """A base class for interacting with the formsite API. Allows user to browse forms, fetch results, write them to a file and to download files uploaded via formsite."""
        self.form_id = form_id
        self.params = formsite_params
        self.login = login
        self.url_base = f"https://{login.server}.formsite.com/api/v2/{login.directory}"
        self.url_files = f"https://{self.login.server}.formsite.com/{self.login.directory}/files/"
        self.authHeader = self.login.getAuthHeader()
        self.paramsHeader = self.params.getParamsHeader()
        self.itemsHeader = self.params.getItemsHeader()
        self.Data = None
        self.Links = None

    def _validate_path(self, path: PathLike, is_folder=False) -> PathLike:
        """Parses input path to posix format. Creates parent directories if they dont exist."""
        try:
            output_file = Path(path).resolve()
            if is_folder:
                if not output_file.exists():
                    output_file.mkdir(parents=True)
            else:
                if not output_file.parent.exists():
                    output_file.parent.mkdir(parents=True)
            return output_file.as_posix()
        except:
            raise Exception("Invalid destination path.")

    def _perform_api_fetch(self, save_results_jsons, save_items_json, refresh_items_json):
        """Entrypoint for performing API calls (asynchronously)."""
        api_handler = _FormsiteAPI(self, save_results_jsons=save_results_jsons,
                                   save_items_json=save_items_json, refresh_items_json=refresh_items_json)
        return asyncio.get_event_loop().run_until_complete(api_handler.Start())

    def _assemble_dataframe(self, items: str, results: list) -> pd.DataFrame:
        """Entrypoint for assembling a pandas dataframe from received API data (uses multiprocessing)."""
        if self.params.sort == 'desc':
            sort = False
        else:
            sort = True
        processing_handler = _FormsiteProcessing(
            items, results, self, sort_asc=sort)
        return processing_handler.Process()

    def FetchResults(self, save_results_jsons=False, save_items_json=False, refresh_items_json=False) -> None:
        """Fetches results from formsite API according to specified parameters. Updates the `self.Data` variable which stores the dataframe."""
        items, results = self._perform_api_fetch(
            save_results_jsons=save_results_jsons, save_items_json=save_items_json, refresh_items_json=refresh_items_json)
        self.Data = self._assemble_dataframe(items, results)

    def ReturnResults(self, save_results_jsons=False, save_items_json=False, refresh_items_json=False) -> pd.DataFrame():
        """Returns pandas dataframe of results. If it doesnt exist yet, creates it."""
        if self.Data is None:
            self.FetchResults(save_results_jsons=save_results_jsons,
                              save_items_json=save_items_json, refresh_items_json=refresh_items_json)
        return self.Data

    def ExtractLinks(self, links_regex='.+') -> None:
        """Stores a set of links in `self.Links` of files saved on formsite servers, that were submitted to the specified form."""
        if self.Data is None:
            self.FetchResults()
        self.Links = set()
        for col in self.Data.columns:
            txt = self.Data[col].to_list()
            try:
                for item in txt:
                    if item.startswith(self.url_files) == True:
                        if regex.search(links_regex, item) is not None:
                            for link in item.split(' | '):
                                if link != '':
                                    self.Links.add(link)                  
            except:
                continue

    async def _list_all_forms(self):
        url_forms = f"{self.url_base}/forms"
        async with request("GET", url_forms, headers=self.authHeader) as response:
            response.raise_for_status()
            content = await response.content.read()
            d = json.loads(content.decode('utf-8'))['forms']
            for row in d:
                for val in row["stats"]:
                    row[val] = row['stats'][val]
            forms_df = pd.DataFrame(
                d, columns=['name', 'state', 'directory', 'resultsCount', 'filesSize'])
            return forms_df

    def ListAllForms(self, display2console=False, save2csv=False):
        forms_df = asyncio.get_event_loop().run_until_complete(self._list_all_forms())
        if display2console:
            pd.set_option('display.max_rows', None)
            print(forms_df)
        if save2csv is not False:
            output_file = self._validate_path(save2csv)
            forms_df.to_csv(output_file, encoding='utf-8', index=False)

    def ReturnLinks(self, links_regex='.+') -> set():
        """Returns a set of links of files saved on formsite servers, that were submitted to the specified form."""
        if self.Links is None:
            self.ExtractLinks(links_regex=links_regex)
            self.ReturnLinks(links_regex=links_regex)
            return
        
        return self.Links

    def WriteLinks(self, destination_path: PathLike, links_regex='.+'):
        """Writes links extracted with `self.ExtractLinks()` to a text file"""
        if self.Links is None:
            self.ExtractLinks(links_regex=links_regex)
            self.WriteLinks(destination_path, links_regex=links_regex)
            return
        output_file = self._validate_path(destination_path)
        with open(output_file, 'w') as writer:
            for link in self.Links:
                writer.write(link+"\n")

    def DownloadFiles(self, download_folder: PathLike, max_concurrent_downloads=10, links_regex='.+') -> None:
        """Downloads files saved on formsite servers, that were submitted to the specified form. Please customize `max_concurrent_downloads` to your specific use case."""
        if self.Links is None:
            self.ExtractLinks(links_regex=links_regex)
            self.DownloadFiles(download_folder, max_concurrent_downloads=max_concurrent_downloads, links_regex=links_regex)
            return

        download_folder = self._validate_path(download_folder, is_folder=True)
        download_handler = _FormsiteDownloader(
            download_folder, self.Links, max_concurrent_downloads)
        asyncio.get_event_loop().run_until_complete(download_handler.Start())

    def ListColumns(self):
        """Prints list of columns (items, usercontrols) and their respective formsite IDs."""
        api_handler = _FormsiteAPI(interface)
        api_handler.check_pages = False
        items, _ = asyncio.get_event_loop().run_until_complete(api_handler.Start())
        items = pd.DataFrame(json.loads(items)['items'], columns=[
                             'id', 'label', 'position'])
        items = items.set_index('id')
        pd.set_option('display.max_rows', None)
        print("only showing user controls and their positon")
        print(f"Results labels: {arguments.resultslabels}")
        print(f"Results view: {arguments.resultsview}")
        print(items)

    def WriteResults(self, destination_path: PathLike, encoding="utf-8", date_format="%Y-%m-%d %H:%M:%S") -> None:
        if self.Data is None:
            self.FetchResults()
            self.WriteResults(destination_path, encoding=encoding, date_format=date_format)
            return

        output_file = self._validate_path(destination_path)

        if regex.search('.+\\.xlsx$', output_file) is not None:
            self.Data.to_excel(output_file, index=False, encoding=encoding)
        else:
            self.Data.to_csv(output_file, index=False,
                             encoding=encoding, date_format=date_format, line_terminator="\n", sep=',')

    def WriteLatestRef(self, destination_path: PathLike):
        if self.Data is None:
            self.FetchResults()
            self.WriteLatestRef(destination_path)
            return

        output_file = self._validate_path(destination_path)
        latest_ref = max(self.Data['Reference #'])
        with open(output_file, 'w') as writer:
            writer.write(latest_ref)

class _FormsiteAPI:
    def __init__(self, interface: FormsiteInterface, save_results_jsons=False, save_items_json=False, refresh_items_json=False):
        self.paramsHeader = interface.paramsHeader
        self.itemsHeader = interface.itemsHeader
        self.authHeader = interface.authHeader
        self.form_id = interface.form_id
        self.total_pages = 1
        self.results_url = f'{interface.url_base}/forms/{interface.form_id}/results'
        self.items_url = f'{interface.url_base}/forms/{interface.form_id}/items'
        self.save_results_jsons = save_results_jsons
        self.save_items_json = save_items_json
        self.refresh_items_json = refresh_items_json
        self.check_pages = True

    async def Start(self):
        """Performs all API calls to formsite servers asynchronously"""
        async with ClientSession(headers=self.authHeader, timeout=ClientTimeout(total=None)) as self.session:
            with tqdm(desc='Starting API requests', total=2, unit=' calls', leave=False) as self.pbar:
                self.pbar.desc = "Fetching results"
                self.results = [await self.fetch_results(1)]
                if self.total_pages > 1:
                    self.pbar.total = self.total_pages
                    tasks = set([self.fetch_results(page)
                                 for page in range(2, self.total_pages)])
                    [self.results.append(res) for res in [await t for t in asyncio.as_completed(tasks)]]
                self.pbar.desc = "Fetching items"
                self.items = await self.fetch_items()
                self.pbar.desc = "API calls complete"
        return self.items, self.results

    async def fetch_results(self, page) -> str:
        params = self.paramsHeader
        params['page'] = page
        content = await self.fetch_content(self.results_url, params)
        if self.save_results_jsons:
            await self.write_content(f'./results_{self.form_id}_{page}.json', content)
        self.pbar.update(1)
        return content.decode('utf-8')

    async def write_content(self, filename, content) -> None:
        async with aiofiles.open(filename, 'wb') as writer:
            await writer.write(content)

    async def fetch_content(self, url, params) -> bytes:
        async with self.session.get(url, params=params) as response:
            if self.check_pages == True:
                self.total_pages = int(
                    response.headers['Pagination-Page-Last'])
                self.check_pages = False
            content = await response.content.read()
            if response.status != 200:
                self.pbar.desc = "Reached rate limit, waiting 60 seconds"
                if response.status == 429:
                    await asyncio.sleep(60)
                    self.pbar.desc = "Fetching results"
                    content = await self.fetch_content(url, params)
                else:
                    response.raise_for_status()
        return content

    async def fetch_items(self) -> str:
        content = await self.fetch_content(self.items_url, self.itemsHeader)
        if self.save_items_json:
            await self.write_content(f'./items_{self.form_id}.json', content)
        self.pbar.update(1)
        return content.decode('utf-8')

class _FormsiteProcessing:
    def __init__(self, items: str, results: list, interface: FormsiteInterface, sort_asc=False):
        self.items_json = json.loads(items)
        self.results_jsons = [json.loads(results_page)
                              for results_page in results]
        self.timezone_offset = interface.params.timezone_offset
        ih = pd.DataFrame(self.items_json['items'])['label']
        ih.name = None
        self.columns = ih.to_list()
        self.sort_asc = sort_asc

    def Process(self) -> pd.DataFrame:
        """Return a dataframe in the same format as a regular formsite export."""
        try:
            assert len(self.results_jsons[0]['results']) != 0
        except AssertionError:
            print("No results to process.")
            return None
        splits = self._divide(self.results_jsons, cpu_count())
        pbar = tqdm(total=len(splits)+4, desc='Processing results',
                    leave=False)

        def _update_pbar(f):
            pbar.update(1)
            return f

        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []
            for split in splits:
                if split != []:
                    future = executor.submit(self._process_many, split)
                    future.add_done_callback(_update_pbar)
                    futures.append(future)
            concurrent.futures.wait(futures)
            pbar.update(1)
            dataframe_list = []
            for future in futures:
                dataframe_list.append(future.result())

        pbar.desc = "Combining results"
        pbar.update(1)
        final_dataframe = pd.concat(dataframe_list)
        pbar.desc = "Sorting results"
        pbar.update(1)
        final_dataframe.sort_values(
            by=['Reference #'], ascending=self.sort_asc, inplace=True)
        pbar.desc = "Results processed"
        pbar.update(1)
        return final_dataframe

    def _divide(self, lst, n):
        p = len(lst) // n
        if p == 0:
            return self._divide(lst[p:], n-1)
        elif len(lst)-p > 0:
            return [lst[:p]] + self._divide(lst[p:], n-1)
        else:
            return [lst]

    def _process_many(self, results_jsons_split: list):
        dataframes = []
        for results_json in results_jsons_split:
            dataframe = self._process_one(results_json)
            dataframes.append(dataframe)
        return pd.concat(dataframes)

    def _process_one(self, results_json: dict):
        dataframe_in_progress = self._make_dataframe_page_hardcoded(
            results_json)
        items_df = pd.DataFrame(self._separate_items_single(
            dataframe_in_progress['items']), columns=self.columns)
        df_1, df_2 = self._hardcoded_columns_renaming(
            dataframe_in_progress.reset_index(drop=True))
        final_dataframe = pd.concat([df_1, items_df, df_2], axis=1)
        return final_dataframe

    def _make_dataframe_page_hardcoded(self, results_json: dict) -> pd.DataFrame:
        """Creates a dataframe from a json file for hardcoded columns"""
        dataframe_in_progress = pd.DataFrame(results_json['results'])
        dataframe_in_progress['date_update'] = dataframe_in_progress['date_update'].apply(
            lambda x: self._string2datetime(x, self.timezone_offset))
        dataframe_in_progress['date_start'] = dataframe_in_progress['date_start'].apply(
            lambda x: self._string2datetime(x, self.timezone_offset))
        dataframe_in_progress['date_finish'] = dataframe_in_progress['date_finish'].apply(
            lambda x: self._string2datetime(x, self.timezone_offset))
        dataframe_in_progress['duration'] = dataframe_in_progress['date_finish'] - \
            dataframe_in_progress['date_start']
        dataframe_in_progress['duration'] = dataframe_in_progress['duration'].apply(
            lambda x: x.total_seconds())
        return dataframe_in_progress

    def _separate_items_single(self, unprocessed_dataframe: pd.DataFrame):
        """Separates the items array for each submission in results into desired format"""
        list_of_rows = []
        for row in unprocessed_dataframe:
            processed_row = []
            for cell in row:
                final_value = ""
                try:
                    final_value += cell['value']
                except:
                    for value in cell['values']:
                        final_value += value['value']
                        if len(cell['values']) > 1:
                            # | is a separator used by formsite, found on controls with multiple outputs, such as checkboxes
                            final_value += " | "
                processed_row.append(final_value)
            list_of_rows.append(processed_row)
        return list_of_rows

    def _string2datetime(self, old_date, timezone_offset):
        """Converts ISO datetime string to datetime class"""
        try:
            new_date = dt.strptime(old_date, "%Y-%m-%dT%H:%M:%S"+"Z")
            new_date = new_date - timezone_offset
            return new_date
        except:
            return old_date

    def _hardcoded_columns_renaming(self, main_dataframe):
        """Separates hardcoded values into 2 parts, same way as formsite and renames them to the correct values"""
        main_df_part1 = main_dataframe[['id', 'result_status']]
        main_df_part1.columns = ['Reference #', 'Status']
        main_df_part2 = main_dataframe[['date_update', 'date_start', 'date_finish',
                                        'duration', 'user_ip', 'user_browser', 'user_device', 'user_referrer']]
        main_df_part2.columns = ['Date', 'Start Time', 'Finish Time',
                                 'Duration (s)', 'User', 'Browser', 'Device', 'Referrer']
        return main_df_part1, main_df_part2

class _FormsiteDownloader:
    def __init__(self, download_folder: PathLike, links: set, max_concurrent_downloads: int):
        self.download_folder = download_folder
        self.links = links
        self.semaphore = asyncio.Semaphore(max_concurrent_downloads)

    async def Start(self):
        """Starts download of links."""
        async with ClientSession(connector=TCPConnector(limit=None)) as session:
            with tqdm(total=len(self.links), desc='Downloading files', unit='files', leave=False) as self.pbar:
                tasks = []
                for link in self.links:
                    task = asyncio.create_task(self._download(link, session))
                    tasks.append(task)
                await asyncio.gather(*tasks)
                self.pbar.desc = "Download complete"

    async def _fetch(self, url, session):
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
        except:
            self._fetch(url, session)

    async def _write(self, content, filename):
        async with aiofiles.open(filename, "wb") as writer:
            await writer.write(content)

    async def _download(self, url, session):
        async with self.semaphore:
            content = await self._fetch(url, session)
            filename = f"{self.download_folder}/{url.split('/')[len(url.split('/'))-1]}"
            await self._write(content, filename)
            self.pbar.update(1)

def GatherArguments():
    parser = argparse.ArgumentParser(
        description="Github of author: https://github.com/strny0/formsite-utility\n"
                    "This program performs an export of a specified formsite form with parameters.\n"
                    "A faster alternative to a manual export from the formsite website, that can be used for workflow automation.\n"
                    "Allows for the extraction of assets saved on formsite servers.",
        epilog="More info can be found at Formsite API v2 help page:    \n"
                    "https://support.formsite.com/hc/en-us/articles/360000288594-API    \n"
                    "You can find API related information of your specific form under: [Form Settings > Integrations > Formsite API] \n"
                    "API response error codes table:\n"
                    "| code | description                                 |\n"
                    "| 401  | Authentication info is missing or invalid.  |\n"
                    "| 403  | Forbidden.                                  |\n"
                    "| 404  | Path or object not found.                   |\n"
                    "| 422  | Invalid parameter.                          |\n"
                    "| 429  | Too many requests or too busy.              |\n"
                    "| 5xx  | Unexpected internal error.                  |\n",
                    formatter_class=argparse.RawTextHelpFormatter
    )
    g_login = parser.add_argument_group('Login')
    g_params = parser.add_argument_group('Results Parameters')
    g_functions = parser.add_argument_group('Functions')
    g_func_params = parser.add_argument_group('Functions Parameters')
    g_debug = parser.add_argument_group('Debugging')
    g_nocreds = parser.add_mutually_exclusive_group(required=False)

    g_login.add_argument('-u', '--username', type=str, default=None, required=True,
                         help="Username of the account used to create your API token. Required."
                         )
    g_login.add_argument('-t', '--token', type=str, default=None, required=True,
                         help="Your Formsite API token. Required."
                         )
    g_login.add_argument('-s', '--server', type=str, default=None, required=True,
                         help="Your Formsite server. A part of the url. https://fsX.forms… <- the 'fsX' part. For example 'fs22'. Required."
                         )
    g_login.add_argument('-d', '--directory', type=str, default=None, required=True,
                         help="Your Formsite directory. Can be found under [Share > Links > Directory]. Required."
                         )
    g_params.add_argument('-f', '--form', type=str, default=None, required=True,
                          help="Your Formsite form ID. Can be found under [Share > Links > Directory]. Mostly required."
                          )
    g_params.add_argument('--afterref', type=int, default=0,
                          help="Get results greater than a specified Reference #. \nMust be an integer."
                          )
    g_params.add_argument('--beforeref', type=int, default=0,
                          help="Get results lesser than a specified Reference #. \nMust be an integer."
                          )
    g_params.add_argument('--afterdate', type=str, default="",
                          help="Get results after a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS. \nThis date is in your local timezone, unless specified otherwise."
                          )
    g_params.add_argument('--beforedate', type=str, default="",
                          help="Get results before a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS. \nThis date is in your local timezone, unless specified otherwise."
                          )
    g_params.add_argument('--sort', choices=['asc', 'desc'], type=str,  default="desc",
                          help="Determines how the output CSV will be sorted. Defaults to descending."
                          )
    g_params.add_argument('--resultslabels', type=int, default=10,
                          help="Use specific results labels for your CSV headers. \nDefaults to 0, which takes the first set results labels or if those are not available, default question labels."
                          )
    g_params.add_argument('--resultsview', type=int, default=11,
                          help="Use specific results view for your CSV headers. Defaults to 11 = Items+Statistics. Other values currently not supported"
                          )
    g_params.add_argument('-F', '--date_format',  default="%Y-%m-%d %H:%M:%S",
                          help="Specify a quoted string using python datetime directives to specify what format you want your dates in (column: Date)."
                          "\nDefaults to '%%Y-%%m-%%d %%H:%%M:%%S' which is yyyy-mm-dd HH:MM:SS"
                          "\nYou can find the possible format directives here: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior"
                          )
    g_params.add_argument('-T', '--timezone',  default='local',
                          help="You can use this flag to specify the timezone relative to which you want your results."
                          "\nThis is useful for when your organization is using a single formsite timezone for all subusers"
                          "\nInput either name of the timezone from this list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
                          "\nThe timezone database method accounts for daylight savings time."
                          "\nor an offset in the format +02:00 or +0200 or 0200 for a 2 hour later time (for example) from your LOCAL time"
                          "\n[Examples: offsets]"
                          "\n Offset    Cities (this does not account for daylight savings time)"
                          "\n'-08:00' - Los Angeles, Vancouver, Tijuana"
                          "\n'-07:00' - Denver, Edmonton, Ciudad Juarez"
                          "\n'-06:00' - Mexico City, Chicago, San Salvador"
                          "\n'-05:00' - New York, Toronto, Havana, Lima"
                          "\n'-03:00' - São Paulo, Buenos Aires, Montevideo"
                          "\n'+00:00' - London, Lisbon, Dakar"
                          "\n'+01:00' - Berlin, Rome, Paris, Prague"
                          "\n'+02:00' - Cairo, Kiev, Jerusalem, Athens, Sofia"
                          "\n'+03:00' - Moscow, Istanbul, Baghdad, Addis Ababa"
                          "\n'+04:00' - Dubai, Tbilisi, Yerevan"
                          "\n'+06:00' - Dhaka, Almaty, Omsk"
                          "\n'+07:00' - Jakarta, Ho Chi Minh City, Bangkok, Krasnoyarsk"
                          "\n'+08:00' - China - Shanghai, Taipei, Kuala Lumpur, Singapore, Perth, Manila, Makassar, Irkutsk"
                          "\n'+09:00' - Tokyo, Seoul, Pyongyang, Ambon, Chita"
                          "\n'+10:00' - Sydney, Port Moresby, Vladivostok"
                          "\n"
                          "\n[Examples: database names]"
                          "\n'US/Central'"
                          "\n'Europe/Paris'"
                          "\n'America/New_York'"
                          "\n'Etc/GMT+2'"
                          "\n'MST'"
                          "\n'Asia/Bangkok'"
                          )
    g_functions.add_argument('-o', '--output_file', nargs='?', default=False, const='default',
                             help="Specify output file name and location. \nDefaults to export_yyyymmdd_formid.csv in the folder of the script."
                             )
    g_functions.add_argument('-x', '--extract_links', nargs='?',  default=False, const='default',
                             help="If you include this flag, you will get a text file that has all links that start with formsite url stored. \nYou can specify file name or location, for example '-x C:\\Users\\MyUsername\\Desktop\\download_links.txt'. \nIf you don't specify a location, it will default to the folder of the script."
                             )
    g_functions.add_argument('-D', '--download_links', nargs='?',  default=False, const='default',
                             help="If you include this flag, all formsite links in the export will be downloaded to a folder."
                             "\nYou can specify location, for example `-D 'C:\\Users\\My Username\\Desktop\\downloads'"
                             "\nIf you don't specify a location, it will default to the folder of the script."
                             )
    g_func_params.add_argument('-X', '--links_regex', type=str,  default='.+',
                               help="Keep only links that match the regex you provide. \nWon't do anything if -x or -d arguments are not provided. \nDefaults to '.+'. Example usage: '-X \\.json$' would only give you files that have .json extension."
                               )
    g_func_params.add_argument('-c', '--concurrent_downloads',  default=10, type=int,
                               help="You can specify the number of concurrent download tasks. More for large numbers of small files, less for large files. Default is 10")
    g_functions.add_argument('-S', '--store_latest_ref',  nargs='?',  default=False, const='default',
                             help="If you enable this option, a text file `latest_ref.txt` will be created. \nThis file will only contain the highest reference number in the export. \nIf there are no results in your export, nothign will happen.")
    g_nocreds.add_argument('-V', '--version', action="store_true",  default=False,
                           help="Returns version of the script."
                           )
    g_nocreds.add_argument('-l', '--list_columns', action="store_true",  default=False,
                           help="If you use this flag, program will output mapping of what column belongs to which column ID instead of actually running, useful for figuring out search arguments."
                           "\nRequires login info and form id."
                           )
    g_nocreds.add_argument('-L', '--list_forms', nargs='?',  default=False, const='default',
                           help="By itself, prints all forms, their form ids and status. You can specify a file to save the data into."
                           "\nExample: `-L ./list_of_forms.csv`; `-L` by itself only prints it to console."
                           "\nRequires login info."
                           )
    g_debug.add_argument('--generate_results_jsons', action="store_true",  default=False,
                         help="If you use this flag, program will output raw results in json format from API requests."
                         "\nUseful for debugging purposes."
                         )
    g_debug.add_argument('--generate_items_jsons', action="store_true",  default=False,
                         help="If you use this flag, program will not store headers for later reuse."
                         )
    g_debug.add_argument('--refresh_headers', action="store_true",  default=False,
                         help="If you include this flag, items_formid.json will be re-downloaded with latest headers if they already exist."
                         )
    g_debug.add_argument('-v', '--verbose', action="store_true",  default=False,
                         help="If you use this flag, program will log progress in greater detail."
                         )
    return parser.parse_known_args()[0]

if __name__ == '__main__':
    arguments = GatherArguments()
    parameters = FormsiteParams(
        afterref=arguments.afterref,
        beforeref=arguments.beforeref,
        afterdate=arguments.afterdate,
        beforedate=arguments.beforedate,
        resultslabels=arguments.resultslabels,
        resultsview=arguments.resultsview,
        timezone=arguments.timezone,
        date_format=arguments.date_format,
        sort=arguments.sort)
    credentials = FormsiteCredentials(
        arguments.username, arguments.token, arguments.server, arguments.directory)

    interface = FormsiteInterface(
        arguments.form, credentials, parameters, verbose=arguments.verbose)

    if arguments.version is not False:
        current_version = "1.2.2"

        async def checkver():
            async with request("GET", "https://raw.githubusercontent.com/strny0/formsite-utility/main/version.md") as r:
                content = await r.content.read()
                content = content.decode('utf-8')
                print(f"Current version: {current_version}")
                print(f"Latest release: {content}")
            if content != current_version:
                print('Download latest release from github:')
                print('https://github.com/strny0/formsite-utility')
        asyncio.get_event_loop().run_until_complete(checkver())
        quit()
    if arguments.list_forms is not False:
        if arguments.list_forms == 'default':
            interface.ListAllForms(display2console=True)
        else:
            interface.ListAllForms(display2console=True,
                                   save2csv=arguments.list_forms)
        quit()
    if arguments.list_columns is not False:
        interface.ListColumns()
        quit()

    if arguments.output_file is not False:
        interface.FetchResults(save_results_jsons=arguments.generate_results_jsons,
                               save_items_json=arguments.generate_items_jsons, refresh_items_json=arguments.refresh_headers)
        if arguments.output_file == 'default':
            default_filename = f'./export_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}.csv'
            interface.WriteResults(
                default_filename, date_format=arguments.date_format)
        else:
            interface.WriteResults(arguments.output_file,
                                   date_format=arguments.date_format)
    if arguments.extract_links is not False:
        if arguments.extract_links == 'default':
            default_filename = f'./links_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}.txt'
            interface.WriteLinks(
                default_filename, links_regex=arguments.links_regex)
        else:
            interface.WriteLinks(arguments.extract_links,
                                 links_regex=arguments.links_regex)
    if arguments.download_links is not False:
        if arguments.download_links == 'default':
            default_folder = f'./download_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}'
            interface.DownloadFiles(
                default_folder, max_concurrent_downloads=arguments.concurrent_downloads, links_regex=arguments.links_regex)
        else:
            interface.DownloadFiles(
                arguments.download_links, max_concurrent_downloads=arguments.concurrent_downloads)
    if arguments.store_latest_ref is not False:
        if arguments.store_latest_ref == 'default':
            default_filename = './latest_ref.txt'
            interface.WriteLatestRef(default_filename)
        else:
            interface.WriteLatestRef(arguments.store_latest_ref)
