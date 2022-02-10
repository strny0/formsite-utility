"""

session.py

"""


import requests

from formsite_util.logger import FormsiteLogger


class FormsiteSession:
    """Formsite API HTTP Session object"""

    _instances = {}

    def __new__(cls, *args, **kwargs):
        """Prevents duplicate sessions to same formsite server/directory"""

        key = (frozenset(args), frozenset(kwargs))
        if key in cls._instances:
            instance, count = cls._instances.get(key)
            cls._instances[key] = (instance, count + 1)
        else:
            instance = super().__new__(cls)
            cls._instances[key] = (instance, 1)

        return instance

    def __init__(self, token: str, server: str, directory: str):
        """Create a FormSite session object

        Args:
            token (str): Formsite API Token
            server (str): Formsite Server (fsX.formsite.com)
            directory (str): Formsite User directory

        """

        self.url_base: str = f"https://{server}.formsite.com/api/v2/{directory}"
        self.server = server
        self.directory = directory
        self._session = requests.session()
        self._session.headers.update(
            {"Authorization": f"bearer {token}", "Accept": "application/json"}
        )
        self.logger: FormsiteLogger = FormsiteLogger()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def get(
        self,
        url: str,
        params: dict = None,
    ) -> requests.Response:
        """Wrapper method for requests.Session.get()"""
        with self._session.get(url, params=params) as resp:
            return resp

    def close(self):
        """Close the HTTP session if noone is using it"""
        self._session.close()
        for k, v in self._instances.copy().items():
            if v is self:
                instance, count = self._instances.get(k)
                if count <= 1:
                    del self._instances[k]
                else:
                    self._instances[k] = (instance, count - 1)
