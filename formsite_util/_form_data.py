"""Defines the FormData base class and its logic"""
from __future__ import annotations
import json
from os import PathLike
from typing import Dict, Optional, Union, List
from pathlib import Path
import re
import pandas as pd

# ----
from formsite_util.error import InvalidItemsStructureException
from formsite_util._logger import FormsiteLogger
from formsite_util._form_parser import FormParser


class FormData:
    """Formsite API Form object, representing the data"""

    def __init__(
        self,
        results: Optional[Union[pd.DataFrame, PathLike]] = None,
        items: Optional[Union[dict, PathLike]] = None,
    ) -> None:
        """FormData constructor

        Args:
            results: Pre-initialize with particular results.
            items Pre-initalize with particular items. Defaults to None.

        Raises:
            ValueError: Unsupported cached_results_path serialization format (wrong file extension).
        """
        self._labels: dict = {}
        self._items: dict = {}
        self._results: pd.DataFrame = pd.DataFrame()
        self.logger: FormsiteLogger = FormsiteLogger()

        if isinstance(items, dict):
            self._items = items
        elif isinstance(items, str):
            with open(items, "r", encoding="utf-8") as fp:
                self._items = json.load(fp)

        if self.items is not None:
            self._update_labels()

        if isinstance(results, pd.DataFrame):
            self._results = results
        elif isinstance(results, str):
            ext = results.rsplit(".", 1)[-1]
            if ext == "parquet":
                self._results = pd.read_parquet(results)
            elif ext == "feather":
                self._results = pd.read_feather(results)
            elif ext in ("pkl" "pickle"):
                self._results = pd.read_pickle(results)
            elif ext == "xlsx":
                self._results = pd.read_excel(results)
            elif ext == "hdf":
                self._results = pd.read_hdf(results, key="data")
            else:
                raise ValueError(
                    f"Invalid extension in results_path, '{ext}' is not a supported serialization format."
                )

    def _update_labels(self):
        """Updates self.labels (from current self.items) inplace."""
        if self.items:
            self.labels = FormParser.create_rename_map(self.items)

    @property
    def results(self) -> pd.DataFrame:
        """Formsite data as pandas DataFrame without items labels

        Returns:
            pd.DataFrame: form results
        """
        return self._results

    @results.setter
    def results(self, df: pd.DataFrame) -> None:
        assert isinstance(df, pd.DataFrame)
        if isinstance(self._items, dict):
            self._update_labels()
            a = set(self._labels.keys())
            b = set(df.columns)
            assert a == b, "Items don't match dataframe columns."
        self._results = df

    @results.deleter
    def results(self) -> None:
        del self._results

    @property
    def results_labels(self) -> Optional[pd.DataFrame]:
        """Formsite data as pandas DataFrame with items labels

        Returns:
            pd.DataFrame: form data
        """
        if self.labels is None:
            return None
        else:
            return self._results.rename(columns=self.labels)

    @results_labels.setter
    def results_labels(self, *args, **kwargs):
        raise TypeError("Setting data_labels is forbidden, use _update_labels() method instead.")

    @results_labels.deleter
    def results_labels(self):
        del self._labels


    # Kept for compatibility reasons
    data = results
    data_labels = results_labels

    @property
    def labels(self) -> dict:
        """User defined labels

        Returns:
            Mapping of {id:label, ...}. None if unknown.
        """
        return self._labels

    @labels.setter
    def labels(self, value: dict):
        assert isinstance(value, dict), "Invalid value."
        self._labels = value

    @labels.deleter
    def labels(self):
        del self._labels

    @property
    def items(self) -> Optional[Dict[str, dict]]:
        """Form's result labels object

        Items structure:
            Dictonary with object 'items' [...item...]
            Each item has an `id`, `label` and `position` records

        ```json
        { "items": [
                {'id': '100', 'label': 'label_text', 'position': 1},
                ...
            ]
        }
        ```

        Returns:
            List of records (dicts) or None if not fetched.
        """

        return self._items

    @items.setter
    def items(self, value):
        if isinstance(value, dict) and "items" in value:
            self._items = value
        else:
            raise InvalidItemsStructureException(
                "Passed invalid items object to FormsiteForm,items or FormData.items. Expected a dictionary in the format {'items':[...]}"
            )

    @items.deleter
    def items(self):
        del self._items

    def to_csv(
        self, path: str, labels: bool = True, encoding: str = "utf-8-sig", **kwargs
    ) -> None:
        """Save Formsite form as a csv with reasonable default settings.

        Args:
            path (str): CSV Path or file handle.
            labels (bool, optional): Save dataframe with results labels if True, otherwise with column IDs. Defaults to True.
            encoding (str, optional): Text encoding. Defaults to "utf-8-sig".
            \*\*kwargs: Pandas DataFrame.to_csv kwargs.
        """
        path = Path(path).resolve().as_posix()
        df = self.results_labels if labels else self.results
        
        if df is None:
            raise ValueError("Form doesn't have items defined. It is impossible to create results_labels")

        if "date_format" not in kwargs:
            kwargs["date_format"] = "%Y-%m-%d %H:%M:%S"
        if "index" not in kwargs:
            kwargs["index"] = False
        if "encoding" not in kwargs:
            kwargs["encoding"] = encoding

        df.to_csv(
            path,
            **kwargs,
        )
        self.logger.debug(f"Form Data: Saved form to file '{path}'")

    def to_excel(self, path: str, labels: bool = True, **kwargs) -> None:
        """Save Formsite form as an excel with reasonable default settings (Warning: Slow for large data)"""
        path = Path(path).resolve().as_posix()
        df = self.results_labels if labels else self.results
        if df is None:
            raise ValueError("Form doesn't have items defined. It is impossible to create results_labels")
        if "index" not in kwargs:
            kwargs["index"] = False
        df.to_excel(path, **kwargs)

        self.logger.debug(f"Form Data: Saved form to file '{path}'")

    def __repr__(self) -> str:
        if self.results is not None and self.items is not None:
            return f"<{self.__class__.__name__} with results and items>"
        elif self.results is not None:
            return f"<{self.__class__.__name__} with results>"
        elif self.items is not None:
            return f"<{self.__class__.__name__} with items>"
        else:
            return f"<{self.__class__.__name__} empty>"
