"""Defines utility functions for caching form items and form results."""

from typing import Optional
import json
import pandas as pd

from formsite_util.consts import METADATA_COLS


def items_load(path: str) -> Optional[dict]:
    """Attempts to load items from a file

    Args:
        path (str): Path where the items are stored

    Returns:
        Optional[dict]: Items dict or None if not found
    """
    try:
        with open(path, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError:
        return None


def items_save(items: dict, path: str):
    """Saves items to a file

    Args:
        items (dict): Items dict
        path (str): Path where to store the items
    """
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(items, fp, indent=4)


def items_match_data(items: dict, data_cols: pd.Index) -> bool:
    """Checks if all items column ids in data exist in items dict ids

    Args:
        items (dict): form.items
        data_cols (pd.Index): form.data.columns

    Returns:
        bool: True if they match each other, False if they do not.
    """
    metadata = set(METADATA_COLS.keys())
    results_ids = set(data_cols).difference(metadata)
    item_ids = set(i["id"] for i in items["items"])
    return len(results_ids.difference(item_ids)) == 0


def results_load(path: str) -> pd.DataFrame:
    """Loads data in a file located at `path` specified by serialization format (by file extension)

    Args:
        path (str): Path where the data is stored

    Supported formats are:
        - parquet
        - feather
        - pkl | pickle
        - hdf
    Raises:
        ValueError: In the event of an unsupported serialization format

    Returns:
        Optional[pd.DataFrame]: Loaded data as Pandas DataFrame. Empty if no data exists at specified path
    """
    ext = path.rsplit(".", 1)[-1].lower().strip()
    try:
        if ext == "parquet":
            df = pd.read_parquet(path)
        elif ext == "feather":
            df = pd.read_feather(path)
        elif ext in ("pkl" "pickle"):
            df = pd.read_pickle(path)
        elif ext == "xlsx":
            df = pd.read_excel(path)
        elif ext == "hdf":
            df = pd.read_hdf(path, key="data")
        else:
            raise ValueError(
                f"Invalid extension in path, '{ext}' is not a supported serialization format"
            )
    except FileNotFoundError:
        df = pd.DataFrame()
    except ValueError:  # For json
        df = pd.DataFrame()

    return df


def results_save(data: pd.DataFrame, path: str):
    """Saves data to a file in path in specified serialization format (by file extensions)

    Args:
        data (pd.DataFrame): Pandas DataFrame data
        path (str): Path where to store the data

    Supported formats are:
        - parquet
        - feather
        - pkl | pickle
        - hdf

    Raises:
        ValueError: In the event of unsupported serialization format
    """
    ext = path.rsplit(".", 1)[-1].lower().strip()

    if ext == "parquet":
        data.to_parquet(path)
    elif ext == "feather":
        data.to_feather(path)
    elif ext in ("pkl" "pickle"):
        data.to_pickle(path)
    elif ext == "xlsx":
        data.to_excel(path)
    elif ext == "hdf":
        data.to_hdf(path, key="data")
    else:
        raise ValueError(
            f"Invalid extension in path, '{ext}' is not a supported serialization format"
        )
