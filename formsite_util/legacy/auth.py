"""auth.py submodule, defined FormsiteCredentials class
Raises:
    ValueError: Invalid input when initializing FormsiteCredentials class.
"""

from dataclasses import dataclass
from typing import Dict


def _sanitize_argument(argument: str, chars2remove: Dict[str, str]) -> str:
    """Performs a find and replace on 'argument' based on mapping in chars2remove.

    Args:
        argument (str): text to perform find and replace on
        chars2remove (List[str]): mapping of {find:replace}

    Returns:
        str: sanitized argument
    """
    for key, value in chars2remove.items():
        argument = str(argument).replace(key, value)
    return argument


def _confirm_arg_format(arg_value: str, arg_name: str, flag: str, example: str) -> str:
    """A boiler plate function to display a helpful error message.

    Args:
        arg_value (str): current value of the argument variable
        arg_name (str): exact name of the argument variable
        flag (str): flag used to invoke the argument in terminal
        example (str): correct example value

    Raises:
        ValueError: Raised upon entering the incorrect argumant/format.

    Returns:
        str: the sanitized (quote-less) argument back
    """
    quotes_map = {"'": "", '"': ""}
    if not isinstance(arg_value, str):
        raise ValueError(
            f"invalid format for argument {arg_value}, {arg_name}, "
            f"correct example: {flag} {example}"
        )
    arg_value = _sanitize_argument(arg_value, quotes_map)
    return arg_value


@dataclass
class FormsiteCredentials:
    """Class representing formsite login information.

    Args:
        token (str): API access token

        server (str): formsite server, can be found in your formsite url at the beginning, https://fs_.(...).com

        directory (str): can also be found in your formsite URL, when accessing a specific form

    Returns:
        FormsiteCredentials instance
    """

    token: str
    server: str
    directory: str

    def __post_init__(self) -> None:
        """Confirms validity of input."""
        self.confirm_validity()

    def get_auth_header(self) -> dict:
        """Returns a dictionary sent as a header in the API request for authorization purposes."""
        return {"Authorization": f"bearer {self.token}", "Accept": "application/json"}

    def confirm_validity(self) -> None:
        """Checks if credentials input is in correct format."""
        self.token = _confirm_arg_format(self.token, "token", "-t", "token")
        self.server = _confirm_arg_format(self.server, "server", "-s", "fs1")
        self.directory = _confirm_arg_format(self.directory, "directory", "-d", "Wa37fh")
