"""Defines FormsiteFormsList object and its logic."""

from __future__ import annotations
from pathlib import Path
import pandas as pd
from requests import Session
from formsite_util.form_fetcher import FormFetcher
from formsite_util.logger import FormsiteLogger


def readable_filesize(number: int) -> str:
    """Converts a number (filesize in bytes) to more readable filesize with units."""
    if number is None:
        return None
    reductions = 0
    while number >= 1024:
        number = number / 1024
        reductions += 1
    unit = {0: "", 1: "K", 2: "M", 3: "G", 4: "T", 5: "P", 6: "E"}
    return f"{number:0.2f} {unit.get(reductions, None)}B"


class FormsiteFormsList:
    """Formsite API object, representing list of all forms in a directory"""

    def __init__(
        self,
        token: str,
        server: str,
        directory: str,
    ) -> None:
        """FormsiteFormsList constructor

        Args:
            token (str): Formsite API Token
            server (str): Formsite Server (fsX.formsite.com)
            directory (str): Formsite Directory
        """
        super().__init__()
        self.auth_header = {"Authorization": f"bearer {token}"}
        self._data: pd.DataFrame = pd.DataFrame()
        self.logger: FormsiteLogger = FormsiteLogger()
        self.url_base: str = f"https://{server}.formsite.com/api/v2/{directory}"
        self.url_forms: str = f"{self.url_base}/forms"

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

    def fetch(self):
        """Perform the API Fetch for the list of forms"""
        # GET https://{server}.formsite.com/api/v2/{user_dir}/forms
        with Session() as session:
            session.headers.update(self.auth_header)

            with session.get(self.url_forms) as resp:
                FormFetcher.handle_response(resp)
                data = resp.json()

        self.data = self.parse(data)

    def parse(self, data: dict) -> pd.DataFrame:
        """Parses forms list json into pandas dataframe"""
        print(data)
        rows = []
        for item in data["forms"]:
            row = {
                "form_id": item["directory"],
                "name": item["name"],
                "state": item["state"],
                "results_count": item["stats"]["resultsCount"],
                "files_size": item["stats"].get("filesSize", None),
                "files_size_human": readable_filesize(
                    item["stats"].get("filesSize", None)
                ),
                "url": item["publish"]["link"],
            }
            rows.append(row)

        return pd.DataFrame(rows)

    def to_csv(self, path: str, encoding: str = "utf-8-sig") -> None:
        """Save Formsite forms list as a csv with reasonable default settings"""
        path = Path(path).resolve().as_posix()
        self.data.to_csv(
            path,
            index=False,
            encoding=encoding,
        )

    def to_excel(self, path: str) -> None:
        """Save Formsite forms list as an excel with reasonable default settings"""
        path = Path(path).resolve().as_posix()
        self.data.to_excel(path, index=False)
