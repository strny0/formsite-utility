"""Defines the FormData base class and its logic"""
from __future__ import annotations
import json

from typing import Union, List
from pathlib import Path
import re
import pandas as pd


# ----
from formsite_util.error import InvalidItemsStructureException
from formsite_util.logger import FormsiteLogger
from formsite_util.form_parser import FormParser


class FormData:
    """Formsite API Form object, representing the data"""

    def __init__(
        self, cached_results_path: str = None, cached_items_path: str = None
    ) -> None:
        """FormsiteFormData constructor"""
        self._labels: dict = None
        self._items: dict = None
        self._data: pd.DataFrame = pd.DataFrame()
        self.logger: FormsiteLogger = FormsiteLogger()

        if cached_results_path:
            ext = cached_results_path.rsplit(".", 1)[-1]
            if ext == "parquet":
                results = pd.read_parquet(cached_results_path)
            elif ext == "feather":
                results = pd.read_feather(cached_results_path)
            elif ext in ("pkl" "pickle"):
                results = pd.read_pickle(cached_results_path)
            elif ext == "xlsx":
                results = pd.read_excel(cached_results_path)
            elif ext == "hdf":
                results = pd.read_hdf(cached_results_path, key="data")
            else:
                raise ValueError(
                    f"Invalid extension in results_path, '{ext}' is not a supported serialization format."
                )
            self.data = results

        if cached_items_path:
            with open(cached_items_path, "r", encoding="utf-8") as fp:
                items = json.load(fp)
            self.items = items
            self._update_labels()

    def _update_labels(self):
        """Updates self.labels (from current self.items) inplace."""
        if self.items:
            parser = FormParser()
            self.labels = parser.create_rename_map(self.items)

    @property
    def data(self) -> pd.DataFrame:
        """Formsite data as pandas DataFrame without items labels

        Returns:
            pd.DataFrame: form data
        """
        return self._data

    @data.setter
    def data(self, df) -> None:
        assert isinstance(df, pd.DataFrame), "Invalid value."
        self._data = df

    @data.deleter
    def data(self) -> None:
        del self._data

    @property
    def data_labels(self) -> pd.DataFrame:
        """Formsite data as pandas DataFrame with items labels

        Returns:
            pd.DataFrame: form data
        """
        if self.labels is None:
            return None
        else:
            return self._data.rename(columns=self.labels)

    @data_labels.setter
    def data_labels(self, *args, **kwargs):
        raise TypeError("Setting data for data_labels not allowed")

    @data_labels.deleter
    def data_labels(self):
        pass

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
    def items(self) -> Union[list, None]:
        """Form's result labels object

        Items structure:
            Dictonary with object 'items' [...item...]
            Each item has an `id`, `label` and `position` records

        { "items": [
                {'id': '100', 'label': 'label_text', 'position': 1}, ...
            ]
        }

        Returns:
            List of records or None if not fetched.
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

    def to_csv(self, path: str, labels: bool = True, encoding: str = "utf-8-sig") -> None:
        """Save Formsite form as a csv with reasonable default settings"""
        path = Path(path).resolve().as_posix()
        df = self.data_labels if labels else self.data
        df.to_csv(
            path,
            date_format="%Y-%m-%d %H:%M:%S",
            index=False,
            encoding=encoding,
        )
        self.logger.debug(f"Form Data: Saved form to file '{path}'")

    def to_excel(self, path: str, labels: bool = True) -> None:
        """Save Formsite form as an excel with reasonable default settings (Warning: Slow for large data)"""
        path = Path(path).resolve().as_posix()
        df = self.data_labels if labels else self.data
        df.to_excel(path, index=False)
        self.logger.debug(f"Form Data: Saved form to file '{path}'")

    def extract_urls(self, filter_re_pat=r".+") -> List[str]:
        """Extract all URLs of files uploaded to the form

        Args:
            filter_re_pat (regexp, optional): Output only the URLs that match the input regex. Defaults to r".+".

        Returns:
            List[str]: List of URLs to files uploaded to the form.
        """
        url_re_pat = (
            rf"(https\:\/\/{self.server}\.formsite\.com\/{self.directory}\/files\/.*)"
        )
        url_re = re.compile(url_re_pat)
        urls = set()
        for col in self.data.columns:
            try:
                url_mask: pd.Index = self.data[col].str.fullmatch(url_re) == True
                tmp: pd.Series = self.data[url_mask][col]
                tmp = tmp.str.split("|")
                tmp = tmp.explode().str.strip()
                urls = urls.union(tmp.to_list())
            except AttributeError:
                pass

        # Return all URLs that match filter_re_pat
        filter_re = re.compile(filter_re_pat)
        return sorted([url for url in urls if filter_re.match(url)])
