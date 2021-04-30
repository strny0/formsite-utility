from datetime import datetime as dt
from json import loads
from typing import Any, Iterable
from tqdm.asyncio import tqdm
import pandas as pd
from dataclasses import dataclass

@dataclass
class _FormsiteProcessing:
    items: str
    results: Iterable[str]
    interface: Any
    sort_asc: bool = False

    def __post_init__(self):
        self.items_json = loads(self.items)
        self.results_jsons = [loads(results_page) for results_page in self.results]
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