"""Stores useful constants."""
from csv import QUOTE_ALL, QUOTE_MINIMAL, QUOTE_NONE, QUOTE_NONNUMERIC
from datetime import datetime as dt
from os import linesep

# Columns that appear outside of the "items" object in the response json
METADATA_COLS = {
    "id": "Reference #",
    "result_status": "Status",
    "login_username": "Username",
    "login_email": "Email Address",
    "payment_status": "Payment Status",
    "payment_amount": "Payment Amount Paid",
    "score": "Score",
    "date_update": "Date",
    "date_start": "Start Time",
    "date_finish": "Finish Time",
    "user_ip": "User",
    "user_browser": "Browser",
    "user_device": "Device",
    # "user_os": "OS", # Deprecated, not present in exports
    "user_referrer": "Referrer",
}

HTTP_429_WAIT_DELAY = 60  # seconds
ConnectionError_DELAY = 10  # seconds

QUOTE = {
    "QUOTE_ALL": QUOTE_ALL,
    "QUOTE_MINIMAL": QUOTE_MINIMAL,
    "QUOTE_NONE": QUOTE_NONE,
    "QUOTE_NONNUMERIC": QUOTE_NONNUMERIC,
}
LINE_TERM = {"LF": "\n", "CR": "\r", "CRLF": "\r\n", "os_default": linesep}
TIMESTAMP = dt.now().strftime("%Y-%m-%d--%H-%M-%S")
