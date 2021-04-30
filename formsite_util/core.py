# Author: Jakub Strnad
# Documentation: https://github.com/strny0/formsite-utility

from datetime import datetime as dt
from datetime import timedelta as td
from pathlib import Path
from json import loads
from typing import Any
from pytz import timezone as pytztimezone
from regex import search, compile
import asyncio
from aiohttp import request
from aiofiles import open as aiopen
import pandas as pd
import openpyxl
from dataclasses import dataclass
from formsite_util.downloader import _FormsiteDownloader
from formsite_util.processing import _FormsiteProcessing
from formsite_util.api import _FormsiteAPI

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
    token: str
    server: str
    directory: str

    def __post_init__(self):
        self.confirm_validity()

    def getAuthHeader(self) -> dict:
        """Returns a dictionary sent as a header in the API request for authorization purposes."""
        return {"Authorization": f"bearer {self.token}", "Accept": "application/json"}

    def confirm_validity(self):
        """Checks if credentials input is in correct format."""
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

    def ExtractLinks(self, links_filter_regex=r'.+') -> None:
        """Stores a set of links in `self.Links` of files saved on formsite servers, that were submitted to the specified form."""
        links_filter_regex = compile(links_filter_regex)
        if self.Data is None:
            self.FetchResults()
        self.Links = set()
        # iter through self.Data columns, for each column cast to string, extract regex if it exists, unstack into dataframes and concat them all, then iterate through it and find links
        unproc_links = pd.concat([col.astype(str).str.extractall(f'(https\:\/\/{self.login.server}\.formsite\.com\/{self.login.directory}\/files\/.*)').unstack() for name, col in self.Data.items()])
        for i, item in unproc_links.iteritems():
            for o in item.to_list():
                try:
                    if links_filter_regex.search(o) is not None:
                        [self.Links.add(link) for link in o.split(' | ') if link != '']
                except TypeError:
                    pass
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
            forms_df = pd.DataFrame(d, columns=['name', 'state', 'directory', 'resultsCount', 'filesSize'])
            forms_df['form id'] = forms_df.pop('directory')
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
            self.ExtractLinks(links_filter_regex=links_regex)
            self.ReturnLinks(links_regex=links_regex)
            return
        return self.Links

    def WriteLinks(self, destination_path: str, links_regex=r'.+', sort_descending=True):
        """Writes links extracted with `self.ExtractLinks()` to a text file"""
        if self.Links is None or links_regex != r'.+':
            self.ExtractLinks(links_filter_regex=links_regex)
            self.WriteLinks(destination_path, links_regex=links_regex)
            return
        output_file = self._validate_path(destination_path)
        with open(output_file, 'w') as writer:
            sorted_links = [link + '\n' for link in self.Links]
            sorted_links.sort(reverse=sort_descending)
            writer.writelines(sorted_links)

    def DownloadFiles(self, download_folder: str, max_concurrent_downloads=10, links_regex=r'.+', filename_regex=r'', overwrite_existing=True, report_downloads=False, timeout=80, retries=1) -> None:
        """Downloads files saved on formsite servers, that were submitted to the specified form. Please customize `max_concurrent_downloads` to your specific use case."""
        if self.Links is None:
            self.ExtractLinks(links_filter_regex=links_regex)
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

