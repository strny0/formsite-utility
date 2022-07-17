"""Defines a singleton logger object used by formsite-util."""


import logging


class FormsiteLogger(logging.Logger):
    """Custom logger. Key=formsite"""

    _instance = None
    _init_flag = False

    def __new__(cls, *args, **kwargs):
        """Prevents duplicate instances of this object"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if FormsiteLogger._init_flag:
            return

        super().__init__("formsite", logging.DEBUG)
        FormsiteLogger._init_flag = True
