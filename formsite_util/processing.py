"""
processing.py

This module handles processing of results from API jsons. Returns a dataframe.
"""
from datetime import datetime as dt
from datetime import timedelta as td
from json import loads
from typing import Any, Iterable, List, Tuple
from dataclasses import dataclass
from tqdm.asyncio import tqdm
import pandas as pd


@dataclass
class _FormsiteProcessing:

    """Handles processing of results from API jsons. Invoked with `self.Process()`"""
    items: str
    results: Iterable[str]
    interface: Any
    sort_asc: bool = False
    display_progress: bool = True

    def __post_init__(self):
        """Loads json strings as json objects."""
        self.items_json = loads(self.items)
        self.results_jsons = [loads(results_page) for results_page in self.results]
        self.timezone_offset = self.interface.params.timezone_offset
        self.columns = self._generate_columns()
        self.pbar = tqdm(total=4, desc='Processing results', leave=False) if self.display_progress else None

    def _generate_columns(self) -> List[str]:
        """Generates a list of columns for output dataframe from `items.json`."""
        assert isinstance(self.items_json, dict), "items.json is empty"
        assert len(self.items_json) > 0, "items.json is empty"
        column_names = pd.DataFrame(self.items_json['items'])['label']
        column_names.name = None
        colmns_list = column_names.to_list()
        assert len(colmns_list) > 0, "Columns list is empty"
        return colmns_list

    def Process(self) -> pd.DataFrame:
        """Return a dataframe in the same format as a regular formsite export."""
        self._update_pbar_progress()
        assert len(self.results_jsons[0]['results']) > 0, "No results to process! FetchResults returned an empty list."
        final_dataframe = self._init_process(self.results_jsons)
        self._update_pbar_progress()
        self._update_pbar_desc(desc="Sorting results")
        self._update_pbar_progress()
        final_dataframe.sort_values(
            by=['Reference #'], ascending=self.sort_asc, inplace=True)
        self._update_pbar_desc(desc="Results processed")
        self._update_pbar_progress()
        try:
            self.pbar.close()
        except AttributeError:
            pass

        assert final_dataframe.shape[0] > 0, "processing handler returned an empty DataFrame"
        return final_dataframe

    def _init_process(self, result_jsons: List[str]) -> pd.DataFrame:
        """Loads jsons in results list as dataframes and concats them."""
        dataframes = tuple(pd.DataFrame(
            results_json['results']) for results_json in result_jsons)
        dataframe = pd.concat(dataframes)
        dataframe = self._process(dataframe)
        return dataframe

    def _process(self, dataframe_in_progress: pd.DataFrame) -> pd.DataFrame:
        """Merges user columns and hardcoded columns in the same way they appear in on formsite."""
        dataframe_in_progress = self._init_dataframe(dataframe_in_progress)
        items_df = pd.DataFrame(self._separate_items(
            dataframe_in_progress['items']), columns=self.columns)
        df_1, df_2 = self._hardcoded_columns_renaming(
            dataframe_in_progress.reset_index(drop=True))
        final_dataframe = pd.concat([df_1, items_df, df_2], axis=1)
        return final_dataframe

    def _init_dataframe(self, dataframe_in_progress: pd.DataFrame) -> pd.DataFrame:
        """Creates a dataframe from a json file for hardcoded columns."""
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

    @staticmethod
    def _separate_items(unprocessed_dataframe: pd.DataFrame) -> List[List[Any]]:
        """Separates the items array for each submission in results into desired format."""
        list_of_rows = []
        for row in unprocessed_dataframe:
            processed_row = []
            for cell in row:
                final_value = ""
                try:
                    final_value += cell['value']
                except KeyError:
                    for value in cell['values']:
                        final_value += value['value']
                        if len(cell['values']) > 1:
                            # | is a separator used by formsite
                            # found on controls with multiple outputs, eg. checkboxes
                            final_value += " | "
                processed_row.append(final_value)
            list_of_rows.append(processed_row)
        return list_of_rows

    @staticmethod
    def _string2datetime(old_date: str, timezone_offset: td) -> dt:
        """Converts ISO datetime string to datetime class."""
        try:
            new_date = dt.strptime(old_date, "%Y-%m-%dT%H:%M:%SZ") # ISO 8601 standard
            new_date = new_date + timezone_offset
            return new_date
        except TypeError:
            return old_date

    @staticmethod
    def _hardcoded_columns_renaming(main_dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Separates hardcoded values into 2 parts, same way as formsite and renames them to the correct values."""
        main_df_part1 = main_dataframe[['id', 'result_status']]
        main_df_part1.columns = ['Reference #', 'Status']
        main_df_part2 = main_dataframe[['date_update', 'date_start', 'date_finish',
                                        'duration', 'user_ip', 'user_browser', 'user_device', 'user_referrer']]
        main_df_part2.columns = ['Date', 'Start Time', 'Finish Time',
                                 'Duration (s)', 'User', 'Browser', 'Device', 'Referrer']

        return main_df_part1, main_df_part2

    def _update_pbar_progress(self) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.update(1)

    def _update_pbar_desc(self, desc: str) -> None:
        if isinstance(self.pbar, tqdm):
            self.pbar.set_description(desc=desc, refresh=True)
