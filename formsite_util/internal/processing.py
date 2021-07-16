"""
processing.py

This module handles processing of results from API jsons. Returns a dataframe.
"""
from __future__ import annotations
from datetime import datetime as dt
from typing import Any, Dict, Iterable
from dataclasses import dataclass
from tqdm import tqdm
import pandas as pd

@dataclass
class _FormsiteProcessing:

    """Handles processing of results from API jsons. Invoked with `self.Process()`"""
    items: dict
    results: Iterable[dict]
    interface: Any
    sort_asc: bool = False
    display_progress: bool = True

    def __post_init__(self):
        """Loads json strings as json objects."""
        self.timezone_offset = self.interface.params.timezone_offset
        self.column_map = self._generate_columns()
        self.metadata_map = self._generate_metadata()

    def _generate_columns(self) -> Dict[int,str]:
        """Creates a dict that maps column id to column label from items_json

        Returns:
            Dict[int,str]: Mapping of ID:Label
        """
        assert isinstance(self.items, dict), "items.json is empty"
        assert len(self.items) > 0, "items.json is empty"
        column_map = dict()
        for item in self.items['items']:
            column_map[int(item['id'])] = item['label']
        colmns_list = list(column_map.values())
        assert len(colmns_list) > 0, "Columns list is empty"
        return column_map

    def _generate_metadata(self) -> Dict[str,str]:
        """Creates a dict that maps metadata_label (hardcoded by formsite) to a friendlier export name

        Returns:
            Dict[str,str]: Mapping of metadata_ID: metadata_Label
        """
        metadata_map = {
            'id':'Reference #',
            'result_status': 'Status',
            'date_start': 'Start Time',
            'date_finish': 'Finish Time',
            'date_update': 'Date',
            'user_ip': 'User',
            'user_browser': 'Browser',
            'user_device': 'Device',
            'user_referrer': 'Referrer',
            'payment_status': 'Payment Status',
            'payment_amount': 'Payment Amount Paid',
            'login_username': 'Login Username',
            'login_email': 'Login Email',
        }
        return metadata_map
       
    def _process_items_row(self, items: dict) -> pd.Series:
        """Converts a single 'items' record to a pandas Series

        Args:
            items (dict): ['items'] key from a results dict record

        Returns:
            pd.Series: a row of the new output csv
        """
        cols = []
        row = []
        for t in items:
            cols.append(int(t['id']))
            if t.get('values') is not None:
                values = []
                for val in t['values']:
                    values.append(val['value'])
                value = ' | '.join(values)
            else:
                value = t['value']
            row.append(value)
        return pd.Series(row, cols)

    def _process_metadata_row(self, result: dict) -> pd.Series:
        """Converts all non-['items'] keys to a pd.Series row

        Args:
            result (dict): an single results json record

        Returns:
            pd.Series: A row containing all metadata-related information
        """
        if 'items' in result:
            del result['items']
        return pd.Series(result)
    
    def _process_row(self, in_json: dict):
        """Merges metadata_row and items_row into a single row.

        Args:
            in_json (dict): a single results record json

        Returns:
            pd.Series: a row
        """
        items = self._process_items_row(in_json['items'])
        metadata = self._process_metadata_row(in_json)
        concated = pd.concat((metadata, items), axis=0)
        return concated
    
    def _reorder_columns(self, df: pd.DataFrame):
        """Orders existing columns into a standard export format.
        First is always Reference #, Status, then Items, then Remaining metadata.

        Args:
            df (pd.DataFrame): Unordered DataFrame

        Returns:
            pd.DataFrame: Ordered DataFrame
        """
        # order:
        # Reference #, Status
        # items
        # Date,Start Time,Finish Time,Duration (s),User,Browser,Device,Referrer
        left_side = []
        right_side = []
        if 'id' in df.columns:
            left_side.append('id')
        if 'result_status' in df.columns:
            left_side.append('result_status')
        middle = [col if (col in df.columns) and (col not in self.metadata_map.keys()) else None for col in list(self.column_map.keys())]
        while None in middle:
            middle.remove(None)
        if 'payment_status' in df.columns:
            right_side.append('payment_status')
        if 'payment_amount' in df.columns:
            right_side.append('payment_amount')
        if 'login_username' in df.columns:
            right_side.append('login_username')
        if 'login_email' in df.columns:
            right_side.append('login_email')
        if 'date_update' in df.columns:
            right_side.append('date_update')
        if 'date_start' in df.columns:
            right_side.append('date_start')
        if 'date_finish' in df.columns:
            right_side.append('date_finish')
        if 'Duration (s)' in df.columns:
            right_side.append('Duration (s)')
        if 'user_ip' in df.columns:
            right_side.append('user_ip')
        if 'user_browser' in df.columns:
            right_side.append('user_browser')
        if 'user_device' in df.columns:
            right_side.append('user_device')
        if 'user_referrer' in df.columns:
            right_side.append('user_referrer')
        
        final = left_side+middle+right_side
        return df[final]
    
    def _cast_dtypes(self, df: pd.DataFrame):
        """Casts the type of each existing column to their standard form.

        Args:
            df (pd.DataFrame): DataFrame with erratic dtypes

        Returns:
            pd.DataFrame: DataFrame with set dtypes
        """
        if 'Reference #' in df.columns:
            df['Reference #'] = df['Reference #'].astype(int)
        if 'Status' in df.columns:
            df['Status'] = df['Status'].astype(str)
        if 'Payment Status' in df.columns:
            df['Payment Status'] = df['Payment Status'].astype(str)
        if 'Payment Amount Paid' in df.columns:
            df['Payment Amount Paid'] = df['Payment Amount Paid'].astype(str)
        if 'Login Username' in df.columns:
            df['Login Username'] = df['Login Username'].astype(str)
        if 'Login Email' in df.columns:
            df['Login Email'] = df['Login Email'].astype(str)
        if 'Date' in df.columns:
            df['Date'] = df['Date'].apply(self._string2datetime)
        if 'Start Time' in df.columns:
            df['Start Time'] = df['Start Time'].apply(self._string2datetime)
        if 'Finish Time' in df.columns:
            df['Finish Time'] = df['Finish Time'].apply(self._string2datetime)
        if 'Duration (s)' in df.columns:
            df['Duration (s)'] = df['Start Time'] - df['Start Time']
            df['Duration (s)'] = df['Duration (s)'].apply(lambda x: x.total_seconds())
        if 'User' in df.columns:
            df['User'] = df['User'].astype(str)
        if 'Browser' in df.columns:
            df['Browser'] = df['Browser'].astype(str)
        if 'Device' in df.columns:
            df['Device'] = df['Device'].astype(str)
        if 'Referrer' in df.columns:
            df['Referrer'] = df['Referrer'].astype(str)
        return df

    def Process(self) -> pd.DataFrame:
        """Loads jsons in results list as dataframes and concats them."""
        results_list = []
        for results in [json['results'] for json in self.results]:
            results_list += results
        
        series_list = [self._process_row(json_row) for json_row in tqdm(results_list, desc="Processing results", 
                                                                        unit=' rows', 
                                                                        ncols=80, 
                                                                        dynamic_ncols=True, 
                                                                        leave=False)]

        dataframe = pd.DataFrame(series_list)
        combined_map = self.column_map
        combined_map.update(self.metadata_map)
        dataframe = self._reorder_columns(dataframe)
        dataframe.rename(columns=combined_map, inplace=True)
        dataframe = self._cast_dtypes(dataframe)
        if self.interface.params.last is not None:
            dataframe = dataframe.sort_values(by=['Reference #'], ascending=self.sort_asc).reset_index(drop=True)
            until = int(self.interface.params.last)
            dataframe = dataframe.head(until)
        dataframe = dataframe.sort_values(by=['Reference #'], ascending=self.sort_asc).reset_index(drop=True)
        return dataframe

    def _string2datetime(self, old_date: str) -> dt:
        """Converts ISO 8601 datetime string to datetime class."""
        try:
            new_date = dt.strptime(old_date, "%Y-%m-%dT%H:%M:%SZ") # ISO 8601 standard
            new_date = new_date + self.timezone_offset
            return new_date
        except TypeError:
            return old_date
