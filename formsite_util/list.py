"""

list.py

"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
from formsite_util.session import FormsiteSession


def readable_filesize(number: int) -> str:
    """Converts a number (filesize in bytes) to more readable filesize with units."""
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
        session: FormsiteSession = None,
        token: str = None,
        server: str = None,
        directory: str = None,
    ) -> None:
        """FormsiteFormsList master constructor

        Args:
            session (FormsiteSession): FormsiteSession object

            OR

            token (str): Formsite API Token
            server (str): Formsite Server (fsX.formsite.com)
            directory (str): Formsite Directory
        """
        super().__init__()
        self._data: pd.DataFrame = pd.DataFrame()
        self.session: FormsiteSession = session
        if (
            session is None
            and token is not None
            and server is not None
            and directory is not None
        ):
            self.session = FormsiteSession(token, server, directory)

        self.forms_url = f"{self.session.url_base}/forms"

    @classmethod
    def from_session(cls, session: FormsiteSession) -> FormsiteFormsList:
        """FormsiteFormsList constructor

        Args:
            session (FormsiteSession): FormsiteSession object
        """
        return cls(session=session)

    @classmethod
    def from_credentials(
        cls,
        token: str,
        server: str,
        directory: str,
    ) -> FormsiteFormsList:
        """FormsiteFormsList constructor

        Args:
            token (str): Formsite API Token
            server (str): Formsite Server (fsX.formsite.com)
            directory (str): Formsite User directory
        """
        return cls(token=token, server=server, directory=directory)

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
        with self.session.get(self.forms_url) as resp:
            data = resp.json()

        self.data = self.parse(data)

    def parse(self, data: dict) -> pd.DataFrame:
        """Parses forms list json into pandas dataframe"""
        rows = []
        for item in data["forms"]:
            row = {
                "form_id": item["directory"],
                "name": item["name"],
                "state": item["state"],
                "results_count": item["stats"]["resultsCount"],
                "files_size": item["stats"]["filesSize"],
                "files_size_human": readable_filesize(item["stats"]["filesSize"]),
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
