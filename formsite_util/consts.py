"""Stores useful constants."""

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
