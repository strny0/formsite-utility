"""
processing.py

This module handles processing of results from API jsons. Returns a dataframe.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, Iterable
from dataclasses import dataclass
from tqdm import tqdm
import pandas as pd


@dataclass
class _FormsiteProcessing:

    """Handles processing of results from API jsons. Invoked with `self.Process()`

    Args:
        `items` (dict): json of the items API response.
        `results` (List[dict]): list of jsons of the results API response.
        `timezone_offset` (timedelta): offset to shift date_update, date_start, date_finish columns by relative to local timezone. Additive, so to subtract, input negative timedelta.
        `sort_asc` (bool, optional): Whether to sort export by ascending (Reference # or Date if applicable). Defaults to False.
        `use_resultslabels` (bool, optional): True: Use question labels or resultslabels if available. False: Use column IDs and metadata names. Defaults to True.
        `display_progress` (int, optional): If True, displays tqdm progressbar. Defaults to True.
        `params_last` (int, optional): Don't forget to trigger this if you are using the `last` parameter. Trimms excess results. Defaults to None.

    Returns:
        _FormsiteProcessing: An instance of the _FormsiteProcessing class. Start API fetches with `.Start()` method.
    """

    items: dict
    results: Iterable[dict]
    timezone_offset: timedelta
    sort_asc: bool = False
    use_resultslabels: bool = True
    display_progress: bool = True
    params_last: int = None

    def __post_init__(self):
        """Loads json strings as json objects."""
        self.column_map = self._generate_columns()
        self.metadata_map = self._generate_metadata()

    def _generate_columns(self) -> Dict[str, str]:
        """Creates a dict that maps column id to column label from items_json

        Returns:
            Dict[int,str]: Mapping of ID:Label
        """
        column_map = dict()
        try:
            for item in self.items["items"]:
                column_map[str(item["id"])] = item["label"]
        except TypeError:
            pass
        return column_map

    def _generate_metadata(self) -> Dict[str, str]:
        """Creates a dict that maps metadata_label (hardcoded by formsite) to a friendlier export name

        Returns:
            Dict[str,str]: Mapping of metadata_ID: metadata_Label
        """
        return {
            "id": "Reference #",
            "result_status": "Status",
            "date_start": "Start Time",
            "date_finish": "Finish Time",
            "date_update": "Date",
            "user_ip": "User",
            "user_browser": "Browser",
            "user_device": "Device",
            "user_referrer": "Referrer",
            "user_os": "OS",
            "payment_status": "Payment Status",
            "payment_amount": "Payment Amount Paid",
            "login_username": "Login Username",
            "login_email": "Login Email",
            "score": "Score",
        }

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
            cols.append(str(t["id"]))
            if t.get("values") is not None:
                values = []
                for val in t["values"]:
                    values.append(val["value"])
                value = " | ".join(values)
            else:
                value = t["value"]
            row.append(value)
        return pd.Series(row, cols)

    def _process_metadata_row(self, result: dict) -> pd.Series:
        """Converts all non-['items'] keys to a pd.Series row

        Args:
            result (dict): an single results json record

        Returns:
            pd.Series: A row containing all metadata-related information
        """
        if "items" in result:
            del result["items"]
        return pd.Series(result)

    def _process_row(self, in_json: dict):
        """Merges metadata_row and items_row into a single row.

        Args:
            in_json (dict): a single results record json

        Returns:
            pd.Series: a row
        """
        items = self._process_items_row(in_json["items"])
        metadata = self._process_metadata_row(in_json)
        concated = pd.concat((metadata, items), axis=0)
        return concated

    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Orders existing columns into a standard export format.
        First is always Reference #, Status, then Items, then Remaining metadata.

        Args:
            df (pd.DataFrame): Unordered DataFrame

        Returns:
            pd.DataFrame: Ordered DataFrame
        """
        left_side = []
        right_side = []
        if "id" in df.columns:
            left_side.append("id")
        if "result_status" in df.columns:
            left_side.append("result_status")

        if len(self.column_map.keys()) > 0:
            middle = [
                col
                if (col in df.columns) and (col not in self.metadata_map.keys())
                else None
                for col in list(self.column_map.keys())
            ]
        else:
            middle = []
            for col in list(df.columns):
                if col not in list(self.metadata_map.keys()):
                    middle.append(col)

        while None in middle:
            middle.remove(None)
        if "payment_status" in df.columns:
            right_side.append("payment_status")
        if "payment_amount" in df.columns:
            right_side.append("payment_amount")
        if "login_username" in df.columns:
            right_side.append("login_username")
        if "login_email" in df.columns:
            right_side.append("login_email")
        if "score" in df.columns:
            right_side.append("score")
        if "date_update" in df.columns:
            right_side.append("date_update")
        if "date_start" in df.columns:
            right_side.append("date_start")
        if "date_finish" in df.columns:
            right_side.append("date_finish")
        if "Duration (s)" in df.columns:
            right_side.append("Duration (s)")
        if "user_ip" in df.columns:
            right_side.append("user_ip")
        if "user_browser" in df.columns:
            right_side.append("user_browser")
        if "user_device" in df.columns:
            right_side.append("user_device")
        if "user_referrer" in df.columns:
            right_side.append("user_referrer")

        final = left_side + middle + right_side
        return df[final]

    def _cast_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Casts the type of each existing column to their standard form.

        Args:
            df (pd.DataFrame): DataFrame with erratic dtypes

        Returns:
            pd.DataFrame: DataFrame with set dtypes
        """
        if "id" in df.columns:
            df["id"] = df["id"].astype(int, errors="ignore")
        if "result_status" in df.columns:
            df["result_status"] = df["result_status"].astype(str)
        if "payment_status" in df.columns:
            df["payment_status"] = df["payment_status"].astype(str)
        if "payment_amount" in df.columns:
            df["payment_amount"] = df["payment_amount"].astype(str)
        if "login_username" in df.columns:
            df["login_username"] = df["login_username"].astype(str)
        if "score" in df.columns:
            df["score"] = df["score"].astype(int, errors="ignore")
        if "login_email" in df.columns:
            df["login_email"] = df["login_email"].astype(str)
        if "date_update" in df.columns:
            df["date_update"] = df["date_update"].apply(self._string2datetime)
        if "date_start" in df.columns:
            df["date_start"] = df["date_start"].apply(self._string2datetime)
        if "date_finish" in df.columns:
            df["date_finish"] = df["date_finish"].apply(self._string2datetime)
        if "Duration (s)" in df.columns:
            df["Duration (s)"] = df["Start Time"] - df["Start Time"]
            df["Duration (s)"] = df["Duration (s)"].apply(lambda x: x.total_seconds())
        if "user_ip" in df.columns:
            df["user_ip"] = df["user_ip"].astype(str)
        if "user_browser" in df.columns:
            df["user_browser"] = df["user_browser"].astype(str)
        if "user_device" in df.columns:
            df["user_device"] = df["user_device"].astype(str)
        if "user_referrer" in df.columns:
            df["user_referrer"] = df["user_referrer"].astype(str)
        return df

    def _sort_data(self, df: pd.DataFrame, ascending_bool: bool) -> pd.DataFrame:
        try:
            df = df.sort_values(by=["Reference #"], ascending=ascending_bool)
        except KeyError:
            try:
                df = df.sort_values(by=["Date"], ascending=ascending_bool)
            except KeyError:
                pass

        return df.reset_index(drop=True)

    def Process(self) -> pd.DataFrame:
        """Loads jsons in results list as dataframes and concats them."""
        results_list = []
        for results in [json["results"] for json in self.results]:
            results_list += results

        series_list = [
            self._process_row(json_row)
            for json_row in tqdm(
                results_list,
                desc="Processing results",
                unit=" rows",
                ncols=80,
                dynamic_ncols=True,
                leave=False,
            )
        ]

        dataframe = pd.DataFrame(series_list)
        dataframe = self._reorder_columns(dataframe)
        dataframe = self._cast_dtypes(dataframe)
        if self.use_resultslabels:
            combined_map = self.column_map
            combined_map.update(self.metadata_map)
            dataframe.rename(columns=combined_map, inplace=True)
        if self.params_last is not None:
            dataframe = self._sort_data(dataframe, False)
            until = int(self.params_last)
            dataframe = dataframe.head(until)
        dataframe = self._sort_data(dataframe, self.sort_asc)
        return dataframe

    def _string2datetime(self, old_date: str) -> datetime:
        """Converts ISO 8601 datetime string to datetime class."""
        try:
            new_date = datetime.strptime(
                old_date, "%Y-%m-%dT%H:%M:%SZ"
            )  # ISO 8601 standard
            new_date = new_date + self.timezone_offset
            return new_date
        except TypeError:
            return old_date
