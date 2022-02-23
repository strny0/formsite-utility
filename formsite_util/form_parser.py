"""

form_parser.py

"""

from itertools import chain
import re
import pandas as pd

from formsite_util.logger import FormsiteLogger

# Columns that appear outside of the "items" object in the response json
NON_ITEM_COLS = {
    "id": "Reference #",
    "result_status": "Status",
    "login_username": "Username",
    "login_email": "Email Address",
    "payment_status": "Payment Status",
    "payment_amount": "Payment Amount Paid",
    "score": "Score",
    "date_update": "Date",
    "date_start": "Start Time",
    "date_finish": "Finish Time",
    "user_ip": "User",
    "user_browser": "Browser",
    "user_device": "Device",
    # "user_os": "OS", # Deprecated, not present in exports
    "user_referrer": "Referrer",
}


def _parse_item(item: dict):
    """Parses each item in results['results']['items'] to the export format"""
    if "value" in item:
        value = item["value"]
    elif "values" in item:
        values = sorted(item["values"], key=lambda x: x["position"])
        value = " | ".join(v["value"] for v in values)
    return value


def _parse_date_col_inplace(df: pd.DataFrame, col: str):
    """Tries to parse date column (string to datetime) inplace"""
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="raise")


def _order_df_cols(df: pd.DataFrame):
    """Reorders existing dataframe columns into standard export order"""
    final_order = []
    hardcoded_cols = list(NON_ITEM_COLS.keys())
    df_cols = df.columns
    items_cols = set(df_cols).difference(set(hardcoded_cols))
    # ---- left side ----
    left_side = ["id", "result_status", "login_username", "login_email"]
    final_order += [col for col in left_side if col in df_cols]
    # ---- items ----
    final_order += [col for col in df_cols if col in items_cols]
    # ---- right side ----
    final_order += [
        col for col in hardcoded_cols if col in df_cols and col not in final_order
    ]
    # ----
    return df[final_order]


class FormParser:
    """Parses result json into a pandas dataframe"""

    def __init__(self) -> None:
        self.data = []
        self.children_item_re = re.compile(r"(\d+?-\d+?-\d+?)")
        self.logger: FormsiteLogger = FormsiteLogger()

    def parse_results_items(self, items: dict) -> dict:
        """Parses ['items'] dictionary of the result"""
        parsed = {}
        for item in items:
            key = item["id"]
            val = _parse_item(item)
            if self.children_item_re.match(key) is not None:
                s = key.split("-")
                parent_key = f"{s[0]}-{s[-1]}"
                if parent_key not in parsed:
                    parsed[parent_key] = val
                else:
                    parsed[parent_key] = f"{parsed[parent_key]} | {val}"
            else:
                parsed[key] = val
        self.logger.debug(f"Form Parser: Successfully parsed {len(parsed)} results")
        return parsed

    def feed(self, results: dict) -> None:
        """Parses 1 Formsite results dictionary, appends it to processed data"""
        mdc = set(NON_ITEM_COLS.keys())
        for record in results["results"]:
            keyset = set(record.keys())
            metadata = {i: record.get(i) for i in keyset.intersection(mdc)}
            items = self.parse_results_items(record.get("items", {}))
            self.data.append(dict(**metadata, **items))

    def as_dataframe(self) -> pd.DataFrame:
        """Return data fed into the parser so far as a Pandas DataFrame"""
        df = pd.DataFrame(self.data)
        df = _order_df_cols(df)
        _parse_date_col_inplace(df, "date_update")
        _parse_date_col_inplace(df, "date_start")
        _parse_date_col_inplace(df, "date_finish")
        return df

    def as_records(self) -> pd.DataFrame:
        """Return data fed into the parser so far as a 1 json records object"""
        return list(chain(self.data))

    @staticmethod
    def create_rename_map(items: list) -> dict:
        """Creates a mapping for pd.rename(column=...) from items (list of records {id, label, position}."""
        rename_map = {}
        parent_label_map = {}
        label_map = {item["id"]: item["label"] for item in items}
        for item in items:
            key = item["id"]
            if "children" in item:
                for c in item["children"]:
                    parent_label_map[c] = item["label"]
            if key in parent_label_map:
                parent_label = parent_label_map.get(key)
                children = item.get("children")
                if children:
                    idx = int(key.split("-")[-1])
                    if idx < len(children):
                        c = children[int(idx)]
                        prev_label = label_map.get(c)
                        rename_map[key] = f"{prev_label} ({parent_label})"
                else:
                    rename_map[key] = f"{item['label']} ({parent_label})"
            else:
                rename_map[key] = item["label"]
        rename_map.update(NON_ITEM_COLS)
        return rename_map
