"""
core.py 

`FormsiteInterface` `FormsiteParams` and `FormsiteCredentials` classes are defined here.
Author: Jakub Strnad
Documentation: https://github.com/strny0/formsite-utility
"""
import csv
import asyncio
import json
from datetime import datetime as dt
from datetime import timedelta as td
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
import sys
from typing import Any, Optional, Set, Union, Tuple, Dict, List
import re
import pandas as pd
from pytz import UnknownTimeZoneError, timezone as pytztimezone
from aiohttp import request
from formsite_util.downloader import _FormsiteDownloader
from formsite_util.processing import _FormsiteProcessing
from formsite_util.api import _FormsiteAPI

__version__ = '1.2.8.post1'

def _shift_param_date(date: Union[str, dt], timezone_offset: td) -> str:
    if isinstance(date, dt):
        date = date + timezone_offset
    else:
        try:
            date = dt.strptime(str(date), "%Y-%m-%dT%H:%M:%SZ")
            date = date + timezone_offset
        except ValueError:
            try:
                date = dt.strptime(str(date), "%Y-%m-%d")
                date = date + timezone_offset
            except ValueError:
                try:
                    date = dt.strptime(str(date), "%Y-%m-%d %H:%M:%S")
                    date = date + timezone_offset
                except ValueError:
                    raise Exception(
                        'invalid date format input for afterdate/beforedate, '
                        'please use a datetime object or string in ISO 8601, '
                        'yyyy-mm-dd or yyyy-mm-dd HH:MM:SS format')
    return dt.strftime(date, "%Y-%m-%dT%H:%M:%SZ")

def _calculate_tz_offset(timezone: str) -> Tuple[td, dt]:
    """Returns timedelta offset of local datetime to target timezone and local datetime."""
    local_date = dt.now()
    utc_date = dt.utcnow()
    utc_offset = local_date - utc_date
    if re.search(r'(\+|\-|)([01]?\d|2[0-3])([0-5]\d)', timezone) is not None:
        inp = timezone.replace("'", "")
        l_inp = [inp[:2], inp[2:]] if len(inp) == 4 else [inp[:3], inp[3:]]
        offset_from_local = td(hours=int(l_inp[0]), seconds=int(l_inp[1])/60)
    elif re.search(r'(\+|\-|)([01]?\d|2[0-3]):([0-5]\d)', timezone) is not None:
        inp = timezone.replace("'", "")
        l_inp = [inp[:2], inp[3:]] if len(inp) == 5 else [inp[:3], inp[4:]]
        offset_from_local = td(hours=int(l_inp[0]), seconds=int(l_inp[1])/60)
    elif re.search(r'.+/.+', timezone) is not None:
        try:
            inp = pytztimezone(timezone).localize(
                local_date).strftime("%z")
            l_inp = [inp[:2], inp[2:]] if len(inp) == 4 else [inp[:3], inp[3:]]
            inp_td = td(hours=int(l_inp[0]), seconds=int(l_inp[1])/60).total_seconds()
            offset_from_local = td(
                seconds=(inp_td - utc_offset.total_seconds()))
        except UnknownTimeZoneError:
            raise Exception(
                f"UnknownTimeZoneError, '{timezone}' is not a valid tz database name.")
    elif timezone == 'local':
        offset_from_local = td(seconds=0)
    else:
        raise Exception(f"'{timezone}' is invalid tz databse name or offset.")
    return offset_from_local, local_date

def _sanitize_argument(argument: Any, chars2remove: List[str]) -> str:
    """Sanitizes input from `formsite_util.cli`."""
    for _k, _v in chars2remove:
        argument = str(argument).replace(_k, _v)
    return argument

def _confirm_arg_format(argument: str, argument_name: str, flag: str, example: str) -> str:
    """Validates input from `formsite_util.cli`."""
    quotes_map = [('\'', ''), ('\"', '')]
    if not isinstance(argument, str):
        raise Exception(f'invalid format for argument {argument}, {argument_name}, '
                        f'correct example: {flag} {example}')
    argument = _sanitize_argument(argument, quotes_map)
    return argument

def _validate_path(path: str, is_folder=False) -> str:
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
    except Exception as exception:
        raise exception

@dataclass
class FormsiteParams:

    """Parameters class
    This class stores parameters for Formsite requests\n
    `afterref` gets only results greater than integer you provide\n
    `beforeref` gets only results less than integer you provide\n
    `afterdate` gets only results greater than input you provide, expects a `datetime object` or string in `ISO 8601`, `yyyy-mm-dd`, `yyyy-mm-dd HH:MM:SS`\n
    `beforedate` gets only results less than input you provide, expects a `datetime object` or string in `ISO 8601`, `yyyy-mm-dd`, `yyyy-mm-dd HH:MM:SS`\n
    `timezone` sets the timezone dates in results are relative to, also affects input dates. Expects either an offset string in format eg. `+06:00` or database name eg. `America/Chicago`\n
    `date_format` using python datetime directives specify what format you want your dates in your csv output file. Defaults to `%Y-%m-%d %H:%M:%S`\n
    `resultslabels` and `resultsview` More info on Formsite website or FS API of your specific form.\n
    `sort` ( "asc" | "desc" ) sorts results by reference number in ascending or descending order.
    """
    afterref: Optional[int] = None
    beforeref: Optional[int] = None
    afterdate: Optional[Union[str, dt]] = None
    beforedate: Optional[Union[str, dt]] = None
    timezone: str = 'local'
    resultslabels: int = 10
    resultsview: int = 11
    sort: str = "desc"
    col_id_sort: Optional[int] = None
    search_equals: Optional[str] = None
    col_id_equals: Optional[int] = None
    search_contains: Optional[str] = None
    col_id_contains: Optional[int] = None
    search_begins: Optional[str] = None
    col_id_begins: Optional[int] = None
    search_ends: Optional[str] = None
    col_id_ends: Optional[int] = None
    search_method: Optional[str] = None

    def __post_init__(self):
        """Calls `_calculate_tz_offset` internal function."""
        self.timezone_offset, self.local_datetime = _calculate_tz_offset(
            self.timezone)

    def get_params(self, single_page_limit: int = 500) -> dict:
        """Returns a dict that gets parsed as parameters by aiohttp when making a request."""
        results_params: dict[str, Union[str, int]] = dict()
        results_params['page'] = 1
        results_params['limit'] = single_page_limit
        if self.afterref is not None:
            results_params['after_id'] = self.afterref
        if self.beforeref is not None:
            results_params['before_id'] = self.beforeref
        if self.afterdate is not None:
            parsed_afterdate = _shift_param_date(self.afterdate, self.timezone_offset)
            results_params['after_date'] = parsed_afterdate
        if self.beforedate is not None:
            parsed_beforedate = _shift_param_date(self.beforedate, self.timezone_offset)
            results_params['before_date'] = parsed_beforedate
        # 11 = all items + statistics results view
        results_params['results_view'] = self.resultsview
        if self.col_id_sort is not None:
            results_params['sort_id'] = self.col_id_sort
        if self.col_id_equals is not None and self.search_equals is not None:
            results_params[f'search_equals[{self.col_id_equals}]'] = self.search_equals
        if self.col_id_contains is not None and self.search_contains is not None:
            results_params[f'search_contains[{self.col_id_contains}]'] = self.search_contains
        if self.col_id_begins is not None and self.search_begins is not None:
            results_params[f'search_begins[{self.col_id_begins}]'] = self.search_begins
        if self.col_id_ends is not None and self.search_ends is not None:
            results_params[f'search_ends[{self.col_id_ends}]'] = self.search_ends
        if self.search_method is not None:
            results_params['search_method'] = self.search_method
        return results_params

    def get_items(self) -> dict:
        """Returns a dict that gets parsed as parameters by aiohttp when making a request."""
        return {"results_labels": self.resultslabels}

@dataclass
class FormsiteCredentials:

    """Class which represents your user credentials for accessing the formsite API."""
    token: str
    server: str
    directory: str

    def __post_init__(self) -> None:
        """Confirms validity of input."""
        self.confirm_validity()

    def get_auth(self) -> dict:
        """Returns a dictionary sent as a header in the API request for authorization purposes."""
        return {"Authorization": f"bearer {self.token}", "Accept": "application/json"}

    def confirm_validity(self) -> None:
        """Checks if credentials input is in correct format."""
        self.token = _confirm_arg_format(self.token, 'token', '-t', 'token')
        self.server = _confirm_arg_format(self.server, 'server', '-s', 'fs1')
        self.directory = _confirm_arg_format(self.directory, 'directory', '-d', 'Wa37fh')

@dataclass
class FormsiteInterface:

    """A base class for interacting with the formsite API.\n
    Documentation: https://pypi.org/project/formsite-util/\n
    `self.Data` pandas dataframe storing your results.\n
    `self.Links` set storing all formsite links.\n
    Methods of interest:\n
    `FetchResults` stores results in self.Data of the instance of this class.\n
    `ReturnResults` returns a pandas dataframe with the results.\n
    `WriteResults` writes the dataframe to a file.\n
    `ExtractLinks` stores extracted links in self.Links of the instance of this class.\n
    `ReturnLinks` returns a touple with all links.\n
    `WriteLinks` writes them to a file.\n
    `ListAllForms` lists all forms on formsite, output them to console or save them to a file.\n
    `ListColumns` lists all columns and column IDs of a form you set the interface for.\n
    `DownloadFiles` downloads all files submitted to the form to a folder you specify.\n
    `WriteLatestRef` writes highest reference number in results to a file you specify.\n
    `display_progress = False` can be used to disable progressbars in console.
    """

    form_id: str
    auth: FormsiteCredentials
    params: FormsiteParams = FormsiteParams()
    verbose: bool = False
    Data: Optional[pd.DataFrame] = None
    Links: Optional[set] = None
    display_progress: bool = True

    def __post_init__(self):
        """Initializes private variables.\n
        `url_base` is a base url in the format server.formsite.com/api/v2/directory\n
        `url_files` is url_base/files\n
        Also intializes HTTP headers for authorization and parameters.
        """
        self.url_base: str = f"https://{self.auth.server}.formsite.com/api/v2/{self.auth.directory}"
        self.url_files = f"https://{self.auth.server}.formsite.com/{self.auth.directory}/files/"
        self.auth_dict = self.auth.get_auth()
        self.params_dict = self.params.get_params()
        self.items_dict = self.params.get_items()

    def __enter__(self):
        """Allows use of context managers."""
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Allows use of context managers."""
        del self

    def _perform_api_fetch(self,
                           save_results_jsons: bool,
                           save_items_json: bool) -> Tuple[str, Optional[List[str]]]:
        """Entrypoint for performing API calls (asynchronously)."""
        api_handler = _FormsiteAPI(self,
                                   save_results_jsons=save_results_jsons,
                                   save_items_json=save_items_json,
                                   display_progress=self.display_progress)
        api_coroutine = api_handler.Start()
        return asyncio.get_event_loop().run_until_complete(api_coroutine)

    def _assemble_dataframe(self, items: str, results: List[pd.DataFrame]) -> pd.DataFrame:
        """Returns a pandas dataframe from received API data."""
        if self.params.sort == 'desc':
            sort = False
        else:
            sort = True
        processing_handler = _FormsiteProcessing(items,
                                                 results,
                                                 self,
                                                 sort_asc=sort,
                                                 display_progress=self.display_progress)
        return processing_handler.Process()

    def FetchResults(self,
                     save_results_jsons: bool = False,
                     save_items_json: bool = False) -> None:
        """Fetches results from formsite API according to specified parameters.\n
        Updates the `self.Data` variable which stores the dataframe.
        """
        assert len(self.form_id) > 0, f"You must pass form id when instantiating FormsiteCredentials('form_id', login, params=...) you passed '{self.form_id}'"
        items, results = self._perform_api_fetch(save_results_jsons=save_results_jsons,
                                                 save_items_json=save_items_json)
        self.Data = self._assemble_dataframe(items, results)

    def ReturnResults(self,
                      save_results_jsons: bool = False,
                      save_items_json: bool = False) -> pd.DataFrame:
        """Returns pandas dataframe of results."""
        if self.Data is None:
            self.FetchResults(save_results_jsons=save_results_jsons,
                              save_items_json=save_items_json)
        return self.Data

    def ExtractLinks(self, links_filter_re: str = r'.+') -> None:
        """Stores a set of links in `self.Links` of files saved on formsite servers, that were submitted to the specified form."""
        if self.Data is None:
            self.FetchResults()
        links_re = fr'(https\:\/\/{self.auth.server}\.formsite\.com\/{self.auth.directory}\/files\/.*)'
        # iter through self.Data columns,
        # for each column cast to string,
        # extract regex if it exists,
        # unstack into dataframes and concat them all,
        # then iterate through it and keep only links that match regex filter
        link_columns = pd.concat([col.astype(str).str.extractall(links_re).unstack() for _, col in self.Data.items()])
        links_filter_pattern = re.compile(links_filter_re)
        self.Links = set()
        for _, item in link_columns.iteritems():
            for url_raw in item.to_list():
                try:
                    if links_filter_pattern.search(url_raw) is not None:
                        _ = [self.Links.add(url) for url in url_raw.split(' | ') if url != '']
                except TypeError:
                    pass
                except AttributeError:
                    pass

    def human_friendly_filesize(self, number: int) -> str:
        """Converts a number (filesize in bytes) to more readable filesize with units."""
        reductions = 0
        while number >= 1024:
            number = number / 1024
            reductions += 1
        unit = {0: '', 1:'K', 2:'M', 3:'G', 4:'T'}
        return f"{number:0.2f} {unit.get(reductions, None)}B"

    async def _list_all_forms(self) -> pd.DataFrame:
        url_forms = f"{self.url_base}/forms"
        async with request("GET", url_forms, headers=self.auth_dict) as response:
            response.raise_for_status()
            content = await response.content.read()
            all_forms_json = json.loads(content.decode('utf-8'))['forms']
            # un-nest the stats object
            for row in all_forms_json:
                for val in row["stats"]:
                    row[val] = row['stats'][val]
            for row in all_forms_json:
                for val in row["publish"]:
                    row[val] = row['publish'][val]
            forms_df = pd.DataFrame(all_forms_json,columns=['name', 'state', 'directory', 'resultsCount', 'filesSize', 'embed_code', 'link'])
            forms_df['form_id'] = forms_df.pop('directory')
            return forms_df

    def ListAllForms(self,
                     sort_by: str = 'name',
                     display: bool = False,
                     save2csv: Union[str, bool] = False) -> None:
        """Prints name, id, results count, filesize and status of all forms into console or csv.
        You can sort in descending order by `name` `form_id` `resultsCount` `filesSize`.
        """
        forms_df = asyncio.get_event_loop().run_until_complete(self._list_all_forms())
        if display:
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 42) # ensures width < 80 cols
            forms_df = forms_df[['name','resultsCount','filesSize','form_id']]
            forms_df.sort_values(by=[sort_by], inplace=True, ascending=False, ignore_index=True)
            forms_df = forms_df.append({'name':'Total:', 'resultsCount':forms_df['resultsCount'].sum(), 'filesSize':forms_df['filesSize'].sum(),'form_id':f'{forms_df.shape[0]} forms'}, ignore_index=True)
            forms_df['filesSize'] = forms_df['filesSize'].apply(lambda x: self.human_friendly_filesize(int(x)))
            forms_df.set_index('name',inplace=True)
            print(forms_df)
            
        if save2csv is not False:
            forms_df.sort_values(by=[sort_by], inplace=True, ascending=False)
            forms_df.set_index('name',inplace=True)
            output_file = _validate_path(str(save2csv))
            forms_df.to_csv(output_file, encoding='utf-8')

    def ReturnLinks(self, links_regex: str = r'.+') -> Set[str]:
        """Returns a set of urls of files saved on formsite servers."""
        if self.Links is None or links_regex != r'.+':
            self.ExtractLinks(links_filter_re=links_regex)
        return self.Links

    def WriteLinks(self,
                   destination_path: str,
                   links_regex: str = r'.+',
                   sort_descending: bool = True) -> None:
        """Writes links extracted with `self.ExtractLinks()` to a .txt file."""
        if self.Links is None or links_regex != r'.+':
            self.ExtractLinks(links_filter_re=links_regex)
        output_file = _validate_path(destination_path)
        sorted_links = [link + '\n' for link in self.Links]
        sorted_links.sort(reverse=sort_descending)
        with open(output_file, 'w') as writer:
            writer.writelines(sorted_links)

    def DownloadFiles(self,
                      download_folder: str,
                      max_concurrent_downloads: int = 10,
                      links_regex: str = r'.+',
                      filename_regex: str = r'',
                      overwrite_existing: bool = True,
                      report_downloads: bool = False,
                      timeout: int = 80,
                      retries: int = 1,
                      strip_prefix: bool = False) -> None:
        """Downloads files saved on formsite servers, that were submitted to the specified form.\n
        Please customize `max_concurrent_downloads` to your specific use case.
        """
        if self.Links is None:
            self.ExtractLinks(links_filter_re=links_regex)
        assert len(self.Links) > 0, f"There are no files to be downloaded for form {self.form_id}"

        download_folder = _validate_path(download_folder, is_folder=True)
        download_handler = _FormsiteDownloader(download_folder,
                                               self.Links,
                                               max_concurrent_downloads,
                                               overwrite_existing=overwrite_existing,
                                               filename_regex=filename_regex,
                                               report_downloads=report_downloads,
                                               timeout=timeout,
                                               retries=retries,
                                               display_progress=self.display_progress,
                                               strip_prefix=strip_prefix)
        asyncio.get_event_loop().run_until_complete(download_handler.Start())

    def ListColumns(self) -> None:
        """Prints list of columns (items, usercontrols) and their respective formsite IDs."""
        api_handler = _FormsiteAPI(self)
        api_handler.check_pages = False
        items = asyncio.get_event_loop().run_until_complete(
            api_handler.Start(only_items=True))
        items = pd.DataFrame(json.loads(items)['items'], columns=['id', 'label', 'position'])
        items = items.set_index('id')
        pd.set_option('display.max_rows', None)
        print(items)
        print('----------------')
        print(f"Results labels: {self.params.resultslabels}")
        print(f"Results view: {self.params.resultsview}")

    def WriteResults(self, destination_path: str,
                     encoding: str = "utf-8",
                     line_terminator: str = '\n',
                     separator: str = ",",
                     date_format: str = "%Y-%m-%d %H:%M:%S",
                     quoting: int = csv.QUOTE_MINIMAL) -> None:
        """Writes `self.Data` to a file based on provided extension.\n
        Supported output formats are (`.csv`|`.xlsx`|`.pkl`|`.pickle`|`.json`|`.parquet`|`.md`|`.txt`)
        """
        if self.Data is None:
            self.FetchResults()
        output_file = _validate_path(destination_path)
        if re.search('.+\\.txt$', output_file) is not None:
            self.Data.to_string(output_file, encoding=encoding, index=False)
        elif re.search('.+\\.pkl$', output_file) is not None or re.search('.+\\.pickle$', output_file) is not None:
            self.Data.to_pickle(output_file)
        elif re.search('.+\\.parquet$', output_file) is not None:
            self.Data.to_parquet(output_file, index=False)
        elif re.search('.+\\.md$', output_file) is not None:
            self.Data.to_markdown(output_file, index=False)
        elif re.search('.+\\.json$', output_file) is not None:
            try:
                self.Data.to_json(output_file, orient='records', date_format='iso')
            except ValueError:
                renamer: dict[Any, Any] = defaultdict()
                for column_name in self.Data.columns[self.Data.columns.duplicated(keep=False)].tolist():
                    if column_name not in renamer:
                        renamer[column_name] = [column_name+'_0']
                    else:
                        renamer[column_name].append(
                            column_name + '_'+str(len(renamer[column_name])))
                self.Data.rename(columns=lambda column_name: renamer[column_name].pop(
                    0) if column_name in renamer else column_name).to_json(output_file, orient='records', date_format='iso')
        elif re.search('.+\\.xlsx$', output_file) is not None:
            print('Writing to excel (this can be slow for large files!)')
            self.Data.to_excel(output_file, index=False,
                               engine='openpyxl', freeze_panes=(1, 1))
        else:
            self.Data.to_csv(output_file, index=False, chunksize=1024, encoding=encoding,
                             date_format=date_format, line_terminator=line_terminator, sep=separator, quoting=quoting)

    def WriteLatestRef(self, destination_path: str) -> None:
        """Writes `max(self.Data['Reference #])` to a file."""
        if self.Data is None:
            self.FetchResults()

        output_file = _validate_path(destination_path)
        latest_ref = max(self.Data['Reference #'])
        with open(output_file, 'w') as writer:
            writer.write(latest_ref)
