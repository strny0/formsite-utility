# Author: Jakub Strnad
# Documentation: https://github.com/strny0/formsite-utility

from datetime import datetime as dt
from datetime import timedelta as td
from pathlib import Path
from json import loads
from typing import Any, Iterable
from tqdm.asyncio import tqdm
import os
from pytz import timezone as pytztimezone
from regex import search, compile
import asyncio
from aiohttp import ClientSession, ClientTimeout, TCPConnector, request, ClientResponseError, InvalidURL
from aiofiles import open as aiopen
import pandas as pd
import openpyxl
from dataclasses import dataclass
import shutil

@dataclass
class FormsiteParams:
    """This class stores parameters for Formsite requests\n
    `afterref` gets only results greater than integer you provide\n
    `beforeref` gets only results less than integer you provide\n
    `afterdate` gets only results greater than integer you provide, expects a `datetime object` or string in `ISO 8601`, `yyyy-mm-dd`, `yyyy-mm-dd HH:MM:SS`\n
    `beforedate` gets only results less than integer you provide, expects a `datetime object` or string in `ISO 8601`, `yyyy-mm-dd`, `yyyy-mm-dd HH:MM:SS`\n
    `timezone` sets the timezone dates in results are relative to, also affects input dates. expects either an offset string in format `+06:00` or database name `America/Chicago`\n
    `date_format` using python datetime directives specify what format you want your dates in your csv output file. Defaults to `%Y-%m-%d %H:%M:%S`\n
    `resultslabels` and `resultsview` More info on Formsite website or FS API of your specific form.\n
    `sort` ( "asc" | "desc" ) sorts results by reference number in ascending or descending order.\n
    """
    afterref: int = 0
    beforeref: int = 0
    afterdate: Any = ""
    beforedate: Any = ""
    timezone: str = 'local'
    date_format: str = ""
    resultslabels: int = 10
    resultsview: int = 11
    sort: str = "desc"
    colID_sort: int = 0
    paramSearch_equals: str = ''
    colID_equals: int = 0
    paramSearch_contains: str = ''
    colID_contains: int = 0
    paramSearch_begins: str = ''
    colID_begins: int = 0
    paramSearch_ends: str = ''
    colID_ends: int = 0
    paramSearch_method: str = ''

    def __post_init__(self):
        self.timezone_offset, self.local_datetime = self._calculate_tz_offset(
            self.timezone)

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
        # 11 = all items + statistics results view
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
            date = date + timezone_offset
        except:
            try:
                date = dt.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
                date = date + timezone_offset
            except:
                try:
                    date = dt.strptime(date, "%Y-%m-%d")
                    date = date + timezone_offset
                except:
                    try:
                        date = dt.strptime(date, "%Y-%m-%d %H:%M:%S")
                        date = date + timezone_offset
                    except:
                        raise Exception(
                            'invalid date format input for afterdate/beforedate, please use a datetime object or string in ISO 8601, yyyy-mm-dd or yyyy-mm-dd HH:MM:SS')
        date = dt.strftime(date, "%Y-%m-%dT%H:%M:%SZ")
        return date

    def _calculate_tz_offset(self, timezone):
        """Converts input timezone (offset from local or tz databse name) to an offset relative to local timezone."""
        local_date = dt.now()
        utc_date = dt.utcnow()
        utc_offset = local_date - utc_date
        if search(r'(\+|\-|)([01]?\d|2[0-3])([0-5]\d)', timezone) is not None:
            inp = timezone.replace("'", "")
            inp = [inp[:2], inp[2:]] if len(inp) == 4 else [inp[:3], inp[3:]]
            offset_from_local = td(hours=int(inp[0]), seconds=int(inp[1])/60)
        elif search(r'(\+|\-|)([01]?\d|2[0-3]):([0-5]\d)', timezone) is not None:
            inp = timezone.replace("'", "")
            inp = [inp[:2], inp[3:]] if len(inp) == 5 else [inp[:3], inp[4:]]
            offset_from_local = td(hours=int(inp[0]), seconds=int(inp[1])/60)
        elif search(r'.+/.+', timezone) is not None:
            try:
                inp = pytztimezone(timezone).localize(
                    local_date).strftime("%z")
                inp = [inp[:2], inp[2:]] if len(inp) == 4 else [
                    inp[:3], inp[3:]]
                inp_td = td(hours=int(inp[0]), seconds=int(
                    inp[1])/60).total_seconds()
                offset_from_local = td(
                    seconds=(inp_td - utc_offset.total_seconds()))
            except:
                raise Exception("Invalid timezone format provided")
        elif timezone == 'local':
            offset_from_local = td(seconds=0)
        else:
            raise Exception("Invalid timezone format provided")

        return offset_from_local, local_date

    def getItemsHeader(self) -> dict:
        return {"results_labels": self.resultslabels}


@dataclass
class FormsiteCredentials:
    """Class which represents your user credentials for accessing the formsite API."""
    username: str
    token: str
    server: str
    directory: str

    def __post_init__(self):
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
                f'invalid format for argument {argument}, {argument_name}, correct example: {flag} {example}')
        argument = self._sanitize_argument(argument, quotes_map)
        return argument

    def _sanitize_argument(self, argument, chars2remove) -> str:
        """Sanitizes input from `cli`."""
        for k, v in chars2remove:
            argument = str(argument).replace(k, v)
        return argument


@dataclass
class FormsiteInterface:
    """A base class for interacting with the formsite API. Allows user to browse forms, fetch results, write them to a file and to download files uploaded to your formsite forms.\n
    To use this class, you need to provide `form_id`, more info documenation page, and an instance of the FormsiteCredentials class.\n
    Methods of interest:\n`FetchResults` stores results in self.Data of the instance of this class.\n`ReturnResults` returns a pandas dataframe with the results.\n`WriteResults` writes the dataframe to a file.\n
    `ExtractLinks` stores extracted links in self.Links of the instance of this class.\n`ReturnLinks` returns a touple with all links. \n`WriteLinks` writes them to a file. \n
    `ListAllForms` lists all forms on formsite by either writing them to console or saving them to a file.\n`ListColumns` lists all columns and column IDs of a form you set the interface for. \n
    `DownloadFiles` downloads all files submitted to the form to a folder you specify. \n`WriteLatestRef` writes highest reference number in results to a file you specify.
    """
    form_id: str
    login: FormsiteCredentials
    params: FormsiteParams = FormsiteParams()
    verbose: bool = False

    def __post_init__(self):
        self.url_base: str = f"https://{self.login.server}.formsite.com/api/v2/{self.login.directory}"
        self.url_files = f"https://{self.login.server}.formsite.com/{self.login.directory}/files/"
        self.authHeader = self.login.getAuthHeader()
        self.paramsHeader = self.params.getParamsHeader()
        self.itemsHeader = self.params.getItemsHeader()
        self.Data = None
        self.Links = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass

    def _validate_path(self, path: str, is_folder=False) -> str:
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
        if self.form_id == '':
            raise Exception(
                f"Form ID is empty! You cannot call FormsiteInterface.FetchResults without specifying a valid form id.")
        else:
            items, results = self._perform_api_fetch(
                save_results_jsons=save_results_jsons, save_items_json=save_items_json, refresh_items_json=refresh_items_json)
            self.Data = self._assemble_dataframe(items, results)

    def ReturnResults(self, save_results_jsons=False, save_items_json=False, refresh_items_json=False) -> pd.DataFrame():
        """Returns pandas dataframe of results. If it doesnt exist yet, creates it."""
        if self.Data is None:
            self.FetchResults(save_results_jsons=save_results_jsons,
                              save_items_json=save_items_json, refresh_items_json=refresh_items_json)
        return self.Data

    def ExtractLinks(self, links_regex=r'.+') -> None:
        """Stores a set of links in `self.Links` of files saved on formsite servers, that were submitted to the specified form."""
        links_regex = compile(links_regex)
        if self.Data is None:
            self.FetchResults()
        self.Links = set()
        for col in self.Data.columns:
            try:
                for item in set(filter(lambda x: x.startswith(self.url_files), self.Data[col])):
                    if links_regex.search(item) is not None:
                        [self.Links.add(link)
                         for link in item.split(' | ') if link != '']
            except AttributeError:
                pass

    async def _list_all_forms(self):
        url_forms = f"{self.url_base}/forms"
        async with request("GET", url_forms, headers=self.authHeader) as response:
            response.raise_for_status()
            content = await response.content.read()
            d = loads(content.decode('utf-8'))['forms']
            for row in d:
                for val in row["stats"]:
                    row[val] = row['stats'][val]
            forms_df = pd.DataFrame(
                d, columns=['name', 'state', 'directory', 'resultsCount', 'filesSize'])
            forms_df.sort_values(by=['name'], inplace=True)
            forms_df.reset_index(inplace=True, drop=True)
            return forms_df

    def ListAllForms(self, display2console=False, save2csv=False):
        forms_df = asyncio.get_event_loop().run_until_complete(self._list_all_forms())
        if display2console:
            pd.set_option('display.max_rows', None)
            print(forms_df)
        if save2csv is not False:
            output_file = self._validate_path(save2csv)
            forms_df.to_csv(output_file, encoding='utf-8', index=False)

    def ReturnLinks(self, links_regex=r'.+') -> set():
        """Returns a set of links of files saved on formsite servers, that were submitted to the specified form."""
        if self.Links is None or links_regex != r'.+':
            self.ExtractLinks(links_regex=links_regex)
            self.ReturnLinks(links_regex=links_regex)
            return
        return self.Links

    def WriteLinks(self, destination_path: str, links_regex=r'.+', sort_descending=True):
        """Writes links extracted with `self.ExtractLinks()` to a text file"""
        if self.Links is None or links_regex != r'.+':
            self.ExtractLinks(links_regex=links_regex)
            self.WriteLinks(destination_path, links_regex=links_regex)
            return
        output_file = self._validate_path(destination_path)
        with open(output_file, 'w') as writer:
            sorted_links = [link + '\n' for link in self.Links]
            sorted_links.sort(reverse=sort_descending)
            writer.writelines(sorted_links)

    def DownloadFiles(self, download_folder: str, max_concurrent_downloads=10, links_regex=r'.+', filename_regex=r'', overwrite_existing=True, report_downloads=False, timeout=30, retries=3) -> None:
        """Downloads files saved on formsite servers, that were submitted to the specified form. Please customize `max_concurrent_downloads` to your specific use case."""
        if self.Links is None:
            self.ExtractLinks(links_regex=links_regex)
            self.DownloadFiles(download_folder, max_concurrent_downloads=max_concurrent_downloads,
                               links_regex=links_regex, filename_regex=filename_regex, overwrite_existing=overwrite_existing)
            return

        download_folder = self._validate_path(download_folder, is_folder=True)
        download_handler = _FormsiteDownloader(
            download_folder, self.Links, max_concurrent_downloads, overwrite_existing=overwrite_existing, filename_regex=filename_regex, report_downloads=report_downloads, timeout=timeout, retries=retries)
        asyncio.get_event_loop().run_until_complete(download_handler.Start())

    def ListColumns(self):
        """Prints list of columns (items, usercontrols) and their respective formsite IDs."""
        api_handler = _FormsiteAPI(self)
        api_handler.check_pages = False
        items = asyncio.get_event_loop().run_until_complete(
            api_handler.Start(only_items=True))
        items = pd.DataFrame(loads(items)['items'], columns=[
                             'id', 'label', 'position'])
        items = items.set_index('id')
        pd.set_option('display.max_rows', None)
        print(items)
        print('----------------')
        print(f"Results labels: {self.params.resultslabels}")
        print(f"Results view: {self.params.resultsview}")

    def WriteResults(self, destination_path: str, encoding="utf-8", date_format="%Y-%m-%d %H:%M:%S") -> None:
        if self.Data is None:
            self.FetchResults()
            self.WriteResults(destination_path,
                              encoding=encoding, date_format=date_format)
            return

        output_file = self._validate_path(destination_path)

        if search('.+\\.xlsx$', output_file) is not None:
            print('Writing to excel (this can be slow for large files!)')
            self.Data.to_excel(output_file, index=False,
                               engine='openpyxl', freeze_panes=(1, 1))
        else:
            self.Data.to_csv(output_file, index=False, chunksize=1024,
                             encoding=encoding, date_format=date_format, line_terminator="\n", sep=',')

    def WriteLatestRef(self, destination_path: str):
        if self.Data is None:
            self.FetchResults()
            self.WriteLatestRef(destination_path)
            return

        output_file = self._validate_path(destination_path)
        latest_ref = max(self.Data['Reference #'])
        with open(output_file, 'w') as writer:
            writer.write(latest_ref)


@dataclass
class _FormsiteAPI:
    interface: FormsiteInterface
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
                    results = []
                    first = await self.fetch_results(self.paramsHeader, 1)
                    results.append(first)
                    if self.total_pages > 1:
                        tasks = []
                        self.pbar.total = self.total_pages
                        for page in range(2,self.total_pages+1):
                            tasks.append(asyncio.ensure_future(self.fetch_results(self.paramsHeader, page)))
                    completed_tasks = await asyncio.gather(*tasks)
                    results += completed_tasks
                    self.pbar.set_description("Fetching items")
                    items = await self.fetch_items()
                    self.pbar.set_description("API calls complete")
        return items, results

    async def fetch_results(self, params:dict, page:int) -> str:
        content = await self.fetch_content(self.results_url, params, page=page)
        if self.save_results_jsons:
            await self.write_content(f'./results_{self.form_id}_{page}.json', content)
        self.pbar.set_description(f"Fethching page {params['page']}")
        self.pbar.update(1)
        return content.decode('utf-8')

    async def write_content(self, filename, content) -> None:
        async with aiopen(filename, 'wb') as writer:
            await writer.write(content)

    async def fetch_content(self, url, params, page=None) -> bytes:
        if page is not None:
            params['page'] = page
        async with self.session.get(url, params=params) as response:
            content = await response.content.read()
            if response.status != 200:
                self.pbar.desc = "Reached rate limit, waiting 60 seconds"
                if response.status == 429:
                    await asyncio.sleep(60)
                    self.pbar.desc = "Fetching results"
                    content = await self.fetch_content(url, params, page=page)
                else:
                    response.raise_for_status()
            if self.check_pages == True:
                self.total_pages = int(response.headers['Pagination-Page-Last'])
                self.check_pages = False
        return content

    async def fetch_items(self) -> str:
        content = await self.fetch_content(self.items_url, self.itemsHeader)
        if self.save_items_json:
            await self.write_content(f'./items_{self.form_id}.json', content)
        self.pbar.update(1)
        return content.decode('utf-8')


@dataclass
class _FormsiteProcessing:
    items: str
    results: Iterable[str]
    interface: FormsiteInterface
    sort_asc: bool = False

    def __post_init__(self):
        self.items_json = loads(self.items)
        self.results_jsons = [loads(results_page)
                              for results_page in self.results]
        self.timezone_offset = self.interface.params.timezone_offset
        self.columns = self._generate_columns()

    def _generate_columns(self):
        ih = pd.DataFrame(self.items_json['items'])['label']
        ih.name = None
        return ih.to_list()

    def Process(self) -> pd.DataFrame:
        """Return a dataframe in the same format as a regular formsite export."""
        if len(self.results_jsons[0]['results']) == 0:
            raise Exception(
                f"No results to process! FetchResults returned an empty list.")
        with tqdm(total=3, desc='Processing results', leave=False) as self.pbar:
            final_dataframe = self._init_process(self.results_jsons)
            self.pbar.update(1)
            self.pbar.desc = "Sorting results"
            self.pbar.update(1)
            final_dataframe.sort_values(
                by=['Reference #'], ascending=self.sort_asc, inplace=True)
            self.pbar.desc = "Results processed"
            self.pbar.update(1)
        return final_dataframe

    def _init_process(self, result_jsons: list):
        dataframes = tuple(pd.DataFrame(
            results_json['results']) for results_json in result_jsons)
        dataframe = pd.concat(dataframes)
        dataframe = self._process(dataframe)
        return dataframe

    def _process(self, dataframe_in_progress):
        dataframe_in_progress = self._init_dataframe(dataframe_in_progress)
        items_df = pd.DataFrame(self._separate_items(
            dataframe_in_progress['items']), columns=self.columns)
        df_1, df_2 = self._hardcoded_columns_renaming(
            dataframe_in_progress.reset_index(drop=True))
        final_dataframe = pd.concat([df_1, items_df, df_2], axis=1)
        return final_dataframe

    def _init_dataframe(self, dataframe_in_progress) -> pd.DataFrame:
        """Creates a dataframe from a json file for hardcoded columns"""
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

    def _separate_items(self, unprocessed_dataframe: pd.DataFrame):
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
                            # | is a separator used by formsite, found on controls with multiple outputs, eg. checkboxes
                            final_value += " | "
                processed_row.append(final_value)
            list_of_rows.append(processed_row)
        return list_of_rows

    def _string2datetime(self, old_date, timezone_offset):
        """Converts ISO datetime string to datetime class"""
        try:
            new_date = dt.strptime(old_date, "%Y-%m-%dT%H:%M:%S"+"Z")
            new_date = new_date + timezone_offset
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


@dataclass
class _FormsiteDownloader:
    download_folder: str
    links: Iterable[str]
    max_concurrent_downloads: int = 10
    timeout: int = 80
    retries: int = 3
    overwrite_existing: bool = True
    report_downloads: bool = False
    filename_regex: str = r''

    def __post_init__(self):
        self.filename_regex = compile(self.filename_regex)
        self.semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        self.dl_queue = asyncio.Queue()
        self.status = []
        self.failed_downloads = []
        self.active_workers = self.max_concurrent_downloads
        if self.overwrite_existing == False and len(self.links) > 0:
            url = list(self.links)[0].rsplit('/',1)[0]
            filenames_in_dl_dir = self._list_files_in_download_dir(url)
            self.links = set(self.links) - filenames_in_dl_dir

    async def Start(self):
        """Starts download of links."""
        async with ClientSession(connector=TCPConnector(limit=None), timeout=ClientTimeout(total=self.timeout)) as session:
            with tqdm(total=len(self.links), desc='Downloading files', unit='files', leave=False) as self.pbar:
                [self.dl_queue.put_nowait((link, session, 1))
                 for link in self.links]
                tasks = [asyncio.create_task(self.worker(
                    self.dl_queue, self.semaphore)) for _ in range(self.max_concurrent_downloads)]
                await self.dl_queue.join()
                [task.cancel() for task in tasks]
                self.pbar.desc = "Download complete"
        if len(self.failed_downloads) > 0:
            with open('./failed_downloads.txt', 'w') as writer:
                writer.writelines(self.failed_downloads)
            print(
                f"{len(self.failed_downloads)} files failed to download, please see failed_downloads.txt for more info\n if the error is not 403, try increasing timeout or reducing max concurrent downloads")
        if self.report_downloads == True:
            with open('./downloads_status.txt', 'w') as writer:
                for i in self.status:
                    writer.write(f"{i[0]} ; {i[1]}\n")

    def try_exit(self):
        if len(self.status) >= len(self.links):
            return True
        if self.active_workers > len(self.links) - len(self.status):
            return True

    async def worker(self, queue: asyncio.Queue, semaphore: asyncio.Semaphore):
        while not queue.empty():
            if self.try_exit():
                break
            url, session, attempt = await queue.get()
            try:
                await semaphore.acquire()
                r = await self._download(url, session)
                if r == 0:
                    self.pbar.update(1)
                    queue.task_done()
                    self.status.append([url, 'complete'])
            except Exception as e:
                self.pbar.desc = f"{e}"
                await self._handle_error(url,session,attempt,queue, e)
                self.pbar.desc = "Downloading files"
            finally:
                semaphore.release()
                if self.try_exit():
                    break
        self.active_workers -= 1

    async def _log_status_and_stop(self, queue, exception, url):
        queue.task_done()
        self.status.append([url, f"{exception.__class__} {exception}"])
        self.failed_downloads.append(url+'\n')
        self.pbar.update(1)

    async def _retry(self, queue, session, attempt, url):
        queue.put_nowait((url, session, (attempt+1)))
        await asyncio.sleep(0.1)

    async def _handle_error(self, url: str, session: ClientSession, attempt: int, queue: asyncio.Queue, exception: Exception):
        if type(exception) is ClientResponseError:
            if exception.status == 403:
                await self._log_status_and_stop(queue, exception, url)
            else:
                await self._retry(queue, session, attempt, url)
        elif type(exception) is InvalidURL:
            await self._log_status_and_stop(queue, exception, url)
        elif attempt < self.retries:
            await self._retry(queue, session, attempt, url)
        else:
            await self._log_status_and_stop(queue, exception, url)

    def _list_files_in_download_dir(self, url: str) -> set:
        filenames_in_dir = set()
        for file in os.listdir(self.download_folder):
            filenames_in_dir.add(url+file)
        return filenames_in_dir

    async def _fetch(self, url: str, session: ClientSession, filename:str, target:str, chunk_size:int = 4*1024):
        async with session.get(url) as response:
            #print(f" {response.status} | downloading {url}")
            response.raise_for_status()
            size = int(response.headers.get('content-length', 0)) or None
            with tqdm(desc=filename, total=size, leave=False, unit='b', unit_scale=True, unit_divisor=1024, dynamic_ncols=True) as pbar:
                async with aiopen(target+'.tmp', "wb") as writer:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        await writer.write(chunk)
                        pbar.update(len(chunk))
            shutil.move(target+'.tmp', target)
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

