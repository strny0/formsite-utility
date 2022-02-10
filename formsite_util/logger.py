"""

logger.py

"""


import logging


class FormsiteLogger(logging.Logger):
    """Custom logger. Key=formsite"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Prevents duplicate instances of this object"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        super().__init__("formsite", logging.WARNING)
