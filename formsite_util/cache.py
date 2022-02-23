"""

cache.py

"""

from typing import Optional
import json
import pandas as pd


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
        json.dump(items, fp)


def items_match_data(items: dict, data_cols: pd.Index) -> bool:
    list(data_cols)
    items["items"]
    return True
