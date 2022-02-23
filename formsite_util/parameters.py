"""

parameters.py

"""

from dataclasses import dataclass
from typing import Optional, Union
from datetime import datetime as dt
import pytz

# ----
from formsite_util.form_error import InvalidDateFormatExpection


def try_parse_date(date: Union[dt, str]) -> dt:
    """Attempts to parse a date string from various allowed formats int tz=utc datetime"""
    formats = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]
    i = 0
    while not isinstance(date, dt):
        try:
            date = dt.strptime(date, formats[i])
            break
        except IndexError as ex:
            raise InvalidDateFormatExpection(date) from ex
        except ValueError:
            pass
        finally:
            i += 1
    return date


def shift_date_from_tz_to_utc(date: dt, tz: str) -> dt:
    """Converts a UTC date into UTC - tz_offset date"""
    offset = pytz.timezone(tz).utcoffset(date)
    return date + offset


@dataclass(frozen=True)
class FormsiteParameters:

    """FormsiteParameters class
    This class stores parameters for Formsite requests.\n
    `after_id` gets only results with ID (Reference #) greater than integer you provide.\n
    `before_id` gets only results with ID (Reference #) less than integer you provide.\n
    `after_date` gets only results greater than input you provide, expects a `datetime object` or string in `ISO 8601`, `yyyy-mm-dd`, `yyyy-mm-dd HH:MM:SS`.\n
    `before_date` gets only results less than input you provide, expects a `datetime object` or string in `ISO 8601`, `yyyy-mm-dd`, `yyyy-mm-dd HH:MM:SS`.\n
    `timezone` sets the timezone dates in results are relative to, also affects input dates. Expects timezone name eg. `America/Chicago`. Defaults to `Etc/UTC`.\n
    `date_format` using python datetime directives specify what format you want your dates in your csv output file. Defaults to `%Y-%m-%d %H:%M:%S.`\n
    `resultslabels` and `resultsview` More info on Formsite website or FS API of your specific form.\n
    `sort` ( "asc" | "desc" ) sorts results by reference number in ascending or descending order. Defaults to 'desc'.
    """

    last: Optional[int] = None
    after_id: Optional[int] = None
    before_id: Optional[int] = None
    after_date: Optional[Union[str, dt]] = None
    before_date: Optional[Union[str, dt]] = None
    timezone: Optional[str] = "Etc/UTC"
    resultslabels: Optional[int] = None
    resultsview: Optional[int] = 11
    sort: Optional[str] = "desc"

    def results_params_dict(self, single_page_limit: int = 500) -> dict:
        """Generates a parameters dictionary that is later passed to params= kw argument when making API calls.

        Args:
            single_page_limit (int, optional): Results per page limit, 500 is maximum amount. Defaults to 500.

        Returns:
            dict: params dict
        """
        results_params: dict[str, Union[str, int]] = dict()
        results_params["page"] = 1
        results_params["limit"] = single_page_limit
        if self.after_id is not None:
            results_params["after_id"] = self.after_id
        if self.before_id is not None:
            results_params["before_id"] = self.before_id
        if self.after_date is not None:
            date = try_parse_date(self.after_date)
            date = shift_date_from_tz_to_utc(date, self.timezone)
            results_params["after_date"] = date
        if self.before_date is not None:
            date = try_parse_date(self.after_date)
            date = shift_date_from_tz_to_utc(date, self.timezone)
            results_params["before_date"] = date
        if self.resultsview is not None:  # 11 = all items + statistics results view
            results_params["results_view"] = self.resultsview

        return results_params

    def items_params_dict(self) -> dict:
        """Returns a dict that gets parsed as parameters by aiohttp when making a request."""
        if self.resultslabels is None:
            ret = {}
        elif isinstance(self.resultslabels, int):
            ret = {"results_labels": self.resultslabels}
        else:
            raise ValueError(f"resultslabels must be an int, got '{self.resultslabels}'")

        return ret
