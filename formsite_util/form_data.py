"""

form_data.py

"""

from typing import Union
import pandas as pd
from pathlib import Path

# ----
from formsite_util.form_error import InvalidItemsStructureException
from formsite_util.logger import FormsiteLogger


class FormData:
    """Formsite API Form object, representing the data (without HTTP session)"""

    def __init__(self) -> None:
        """FormsiteFormData constructor"""
        self._uses_items = None
        self._items = None
        self._data = pd.DataFrame()
        self.logger: FormsiteLogger = FormsiteLogger()

    @property
    def data(self) -> pd.DataFrame:
        """Formsite data as pandas DataFrame

        Returns:
            pd.DataFrame: form data
        """
        return self._data

    @data.setter
    def data(self, value):
        assert isinstance(value, pd.DataFrame), "Invalid value."
        self._data = value

    @data.deleter
    def data(self):
        del self._data

    @property
    def uses_items(self) -> Union[bool, None]:
        """Form uses items (labels) as columns instead of the column/metadata IDs

        Returns:
            True if uses items. False if uses column/metadata IDs. None if unknown.
        """
        return self._uses_items

    @uses_items.setter
    def uses_items(self, value):
        assert value in [True, False, None], "Invalid value."
        self._uses_items = value

    @uses_items.deleter
    def uses_items(self):
        del self._uses_items

    @property
    def items(self) -> Union[list, None]:
        """Form's result labels object

        Items structure:
            List of object
            Each object has an `id`, `label` and `position` records
        [
            {'id': '100', 'label': 'formsite control label text', 'position': 1},
            ...
        ]

        Returns:
            List of records or None if not fetched.
        """

        return self._items

    @items.setter
    def items(self, value):
        if isinstance(value, dict):
            self._items = value["items"]
        elif isinstance(value, list):
            self._items = value
        else:
            raise InvalidItemsStructureException(
                "Passed invalid items object to FormsiteForm,items or FormData.items. Expected either a ditionary in the format {'items':[...]} or a list in format [{id:..., ...}, {id:..., ...}]"
            )

    @items.deleter
    def items(self):
        del self._items

    def to_csv(self, path: str, encoding: str = "utf-8-sig") -> None:
        """Save Formsite form as a csv with reasonable default settings"""
        path = Path(path).resolve().as_posix()
        self.data.to_csv(
            path,
            date_format="%Y-%m-%d %H:%M:%S",
            index=False,
            encoding=encoding,
        )
        self.logger.debug(f"Form Data: Saved form to file '{path}'")

    def to_excel(self, path: str) -> None:
        """Save Formsite form as an excel with reasonable default settings (Warning: Slow for large data)"""
        path = Path(path).resolve().as_posix()
        self.data.to_excel(path, index=False)
        self.logger.debug(f"Form Data: Saved form to file '{path}'")
