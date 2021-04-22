#!/usr/bin/env python3
# Author: Jakub Strnad
# Documentation: https://github.com/strny0/formsite-utility

from datetime import datetime as dt  # s
from datetime import timedelta as td  # s
from pathlib import Path as Path  # s
from json import loads  # s
from aiohttp.typedefs import PathLike

from time import perf_counter
from tqdm.asyncio import tqdm  # !
import os
from pytz import timezone as pytztimezone
from regex import sub, search, compile  # !
import asyncio  # !
from aiohttp import ClientSession, ClientTimeout, TCPConnector, request
from aiofiles import open as aiopen
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
        if self.form_id == '':
            raise Exception(f"Form ID is empty! You cannot call FormsiteInterface.FetchResults without specifying a valid form id.")
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
            column_as_list = self.Data[col].to_list()
            try:
                for item in column_as_list:
                    if item.startswith(self.url_files) == True:
                        if links_regex.search(item) is not None:
                            [self.Links.add(link) for link in item.split(' | ') if link != '']
            except:
                continue

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
        if self.Links is None:
            self.ExtractLinks(links_regex=links_regex)
            self.ReturnLinks(links_regex=links_regex)
            return
        return self.Links

    def WriteLinks(self, destination_path: PathLike, links_regex=r'.+'):
        """Writes links extracted with `self.ExtractLinks()` to a text file"""
        if self.Links is None:
            self.ExtractLinks(links_regex=links_regex)
            self.WriteLinks(destination_path, links_regex=links_regex)
            return
        output_file = self._validate_path(destination_path)
        with open(output_file, 'w') as writer:
            sorted_links = [link + '\n' for link in self.Links]
            sorted_links.sort(reverse=True)
            writer.writelines(sorted_links)

    def DownloadFiles(self, download_folder: PathLike, max_concurrent_downloads=10, links_regex=r'.+', filename_regex=r'', overwrite_existing=True) -> None:
        """Downloads files saved on formsite servers, that were submitted to the specified form. Please customize `max_concurrent_downloads` to your specific use case."""
        if self.Links is None:
            self.ExtractLinks(links_regex=links_regex)
            self.DownloadFiles(download_folder, max_concurrent_downloads=max_concurrent_downloads,
                               links_regex=links_regex, filename_regex=filename_regex, overwrite_existing=overwrite_existing)
            return

        download_folder = self._validate_path(download_folder, is_folder=True)
        download_handler = _FormsiteDownloader(
            download_folder, self.Links, max_concurrent_downloads, overwrite_existing=overwrite_existing, filename_regex = filename_regex)
        asyncio.get_event_loop().run_until_complete(download_handler.Start())

    def ListColumns(self):
        """Prints list of columns (items, usercontrols) and their respective formsite IDs."""
        api_handler = _FormsiteAPI(self)
        api_handler.check_pages = False
        items = asyncio.get_event_loop().run_until_complete(api_handler.Start(only_items=True))
        items = pd.DataFrame(loads(items)['items'], columns=[
                             'id', 'label', 'position'])
        items = items.set_index('id')
        pd.set_option('display.max_rows', None)
        print(items)
        print('----------------')
        print(f"Results labels: {self.params.resultslabels}")
        print(f"Results view: {self.params.resultsview}")
        

    def WriteResults(self, destination_path: PathLike, encoding="utf-8", date_format="%Y-%m-%d %H:%M:%S") -> None:
        if self.Data is None:
            self.FetchResults()
            self.WriteResults(destination_path,
                              encoding=encoding, date_format=date_format)
            return

        output_file = self._validate_path(destination_path)

        if search('.+\\.xlsx$', output_file) is not None:
            print('Writing to excel (this can be slow for large files!)')
            self.Data.to_excel(output_file, index=False, engine='openpyxl', freeze_panes=(1,1))
        else:
            self.Data.to_csv(output_file, index=False, chunksize=1024,
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

    async def Start(self, only_items=False):
        """Performs all API calls to formsite servers asynchronously"""
        async with ClientSession(headers=self.authHeader, timeout=ClientTimeout(total=None)) as self.session:
            with tqdm(desc='Starting API requests', total=2, unit=' calls', leave=False) as self.pbar:
                if only_items:
                    items = await self.fetch_items()
                    self.pbar.update(1)
                    return items
                else:
                    self.pbar.desc = "Fetching results"
                    results = []
                    first = await self.fetch_results(1)
                    results.append(first)
                    if self.total_pages > 1:
                        self.pbar.total = self.total_pages
                        tasks = set([self.fetch_results(page)
                                     for page in range(2, self.total_pages+1)])
                        [results.append(res) for res in [await t for t in asyncio.as_completed(tasks)]]
                    self.pbar.desc = "Fetching items"
                    items = await self.fetch_items()
                    self.pbar.desc = "API calls complete"
        return items, results

    async def fetch_results(self, page) -> str:
        params = self.paramsHeader
        params['page'] = page
        content = await self.fetch_content(self.results_url, params)
        if self.save_results_jsons:
            await self.write_content(f'./results_{self.form_id}_{page}.json', content)
        self.pbar.update(1)
        return content.decode('utf-8')

    async def write_content(self, filename, content) -> None:
        async with aiopen(filename, 'wb') as writer:
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
        self.items_json = loads(items)
        self.results_jsons = [loads(results_page) for results_page in results]
        self.timezone_offset = interface.params.timezone_offset
        self.sort_asc = sort_asc
        self.columns = self._generate_columns()

    def _generate_columns(self):
        ih = pd.DataFrame(self.items_json['items'])['label']
        ih.name = None
        return ih.to_list()

    def Process(self) -> pd.DataFrame:
        """Return a dataframe in the same format as a regular formsite export."""
        if len(self.results_jsons[0]['results']) == 0:
            raise Exception(f"No results to process! FetchResults returned an empty list.")
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
        dataframes = tuple(pd.DataFrame(results_json['results']) for results_json in result_jsons)
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
    def __init__(self, download_folder: PathLike, links: set, max_concurrent_downloads: int, overwrite_existing=True, filename_regex=r''):
        self.download_folder = download_folder
        self.filename_regex = compile(filename_regex)
        self.semaphore = asyncio.Semaphore(max_concurrent_downloads)
        if overwrite_existing or len(links) == 0:
            self.links = links
        else:
            url = ''
            for i in tuple(links)[0].split('/')[:-1]:
                url += i + '/'
            filenames_in_dl_dir = self._list_files_in_download_dir(url)
            self.links = links - filenames_in_dl_dir

    async def Start(self):
        """Starts download of links."""
        async with ClientSession(connector=TCPConnector(limit=None)) as session:
            with tqdm(total=len(self.links), desc='Downloading files', unit='files', leave=False) as self.pbar:
                tasks = (asyncio.create_task(self._download(link, session, self.filename_regex)) for link in self.links)
                await asyncio.gather(*tasks)
                self.pbar.desc = "Download complete"

    def _list_files_in_download_dir(self, url: str) -> set:
        filenames_in_dir = set()
        for file in os.listdir(self.download_folder):
            filenames_in_dir.add(url+file)
        return filenames_in_dir

    async def _fetch(self, url, session):
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
        except:
            resp = await self._fetch(url, session)
            return resp

    async def _write(self, content, filename):
        async with aiopen(filename, "wb") as writer:
            await writer.write(content)

    async def _download(self, url, session, filename_regex):
        filename = f"{url.split('/')[-1:][0]}"
        if filename_regex.pattern != '':
            filename = self._regex_substitution(filename, filename_regex)
            filename = f"{self.download_folder}/{filename}"
            filename = self._check_if_file_exists(filename)
        else:
            filename = f"{self.download_folder}/{filename}"
        
        async with self.semaphore:
            content = await self._fetch(url, session)
            await self._write(content, filename)
            self.pbar.update(1)
    
    def _check_if_file_exists(self, filename, n = 0) -> str:
        path = Path(filename).resolve()
        if path.exists():
            temp = filename.rsplit('.', 1)
            if temp[0].endswith(f'_{n}'):
                temp[0] = temp[0][:temp[0].rfind(f'_{n}')]
            try:
                filename = temp[0] + f"_{n+1}." + temp[1]
            except IndexError:
                filename = temp[0] + f"_{n+1}"
            filename = self._check_if_file_exists(filename, n = n+1)
        return filename
    
    def _regex_substitution(self, filename, filename_regex):
        try:
            temp = filename.rsplit('.', 1)
            try:
                filename =f"{filename_regex.sub('', temp[0])}.{temp[1]}"
            except:
                filename =f"{filename_regex.sub('', temp[0])}"
        except:
            filename =f"{filename_regex.sub('', filename)}"
        return filename
        
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
    g_params.add_argument('-f', '--form', type=str, default='',
                          help="Your Formsite form ID. Can be found under [Share > Links > Directory]. Mostly required."
                          )
    g_params.add_argument('--afterref', type=int, default=0,
                          help="Get results greater than a specified Reference #. \nMust be an integer."
                          )
    g_params.add_argument('--beforeref', type=int, default=0,
                          help="Get results lesser than a specified Reference #. \nMust be an integer."
                          )
    g_params.add_argument('--afterdate', type=str, default="",
                          help="Get results after a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
                          "\nThis date is in your local timezone, unless specified otherwise."
                          )
    g_params.add_argument('--beforedate', type=str, default="",
                          help="Get results before a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
                          "\nThis date is in your local timezone, unless specified otherwise."
                          )
    g_params.add_argument('--sort', choices=['asc', 'desc'], type=str,  default="desc",
                          help="Determines how the output CSV will be sorted. Defaults to descending."
                          )
    g_params.add_argument('--resultslabels', type=int, default=0,
                          help="Use specific results labels for your CSV headers."
                          "\nDefaults to 0, which takes the first set results labels or if those are not available, default question labels."
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
                          "\n[Examples: database names] avoid using deprecated ones"
                          "\n'America/Chicago'"
                          "\n'Europe/Paris'"
                          "\n'America/New_York'"
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
                               help="Keep only links that match the regex you provide."
                               "\nWon't do anything if -x or -d arguments are not provided."
                               "\nDefaults to '.+'. Example usage: '-X \\.json$' would only give you files that have .json extension."
                               )
    g_func_params.add_argument('-c', '--concurrent_downloads',  default=10, type=int,
                               help="You can specify the number of concurrent download tasks."
                               "\nMore for large numbers of small files, less for large files."
                               "\nDefault is 10")
    g_func_params.add_argument('-n', '--dont_overwrite_downloads',  default=True, action="store_false",
                               help="If you include this flag, files with the same filenames as you are downloading will not be overwritten and re-downloaded.")
    g_func_params.add_argument('-R', '--filename_regex',  default='', type=str,
                               help="If you include this argument, filenames of the files you download from formsite servers will remove all characters from their name that dont match the regex you provide."
                               "\nExpecting an input of allowed characters, for example: -R '[^A-Za-z0-9\\_\\-]+'"
                               "\nAny files that would be overwritten as a result of the removal of characters will be appended with _1, _2, etc.")
    g_functions.add_argument('-S', '--store_latest_ref',  nargs='?',  default=False, const='default',
                             help="If you enable this option, a text file `latest_ref.txt` will be created. \nThis file will only contain the highest reference number in the export. \nIf there are no results in your export, nothign will happen.")
    g_nocreds.add_argument('-V', '--version', action="store_true",  default=False,
                           help="Returns version of the script."
                           )
    g_nocreds.add_argument('-l', '--list_columns', action="store_true",  default=False,
                           help="If you use this flag, program will output mapping of what column belongs to which column ID instead of actually running, useful for figuring out search arguments."
                           "\nRequires login info and form id. Overrides all other functionality of the program."
                           )
    g_nocreds.add_argument('-L', '--list_forms', nargs='?',  default=False, const='default',
                           help="By itself, prints all forms, their form ids and status. You can specify a file to save the data into."
                           "\nExample: '-L ./list_of_forms.csv' to output to file or '-L' by itself to print to console."
                           "\nRequires login info. Overrides all other functionality of the program."
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

def main():
    t0 = perf_counter()
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
        current_version = "1.2.6.2"
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
        print("export complete")
    if arguments.extract_links is not False:
        if arguments.extract_links == 'default':
            default_filename = f'./links_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}.txt'
            interface.WriteLinks(
                default_filename, links_regex=arguments.links_regex)
        else:
            interface.WriteLinks(arguments.extract_links,
                                 links_regex=arguments.links_regex)
        print("links extracted")
    if arguments.download_links is not False:
        if arguments.download_links == 'default':
            default_folder = f'./download_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}'
            interface.DownloadFiles(
                default_folder, max_concurrent_downloads=arguments.concurrent_downloads, links_regex=arguments.links_regex, filename_regex=arguments.filename_regex, overwrite_existing=arguments.dont_overwrite_downloads)
        else:
            interface.DownloadFiles(
                arguments.download_links, max_concurrent_downloads=arguments.concurrent_downloads, links_regex=arguments.links_regex, filename_regex=arguments.filename_regex, overwrite_existing=arguments.dont_overwrite_downloads)
        print("download complete")
    if arguments.store_latest_ref is not False:
        if arguments.store_latest_ref == 'default':
            default_filename = './latest_ref.txt'
            interface.WriteLatestRef(default_filename)
        else:
            interface.WriteLatestRef(arguments.store_latest_ref)
        print("latest reference saved")

    print(f'done in {(perf_counter() - t0):0.2f} seconds!')

if __name__ == '__main__':
    main()