import json
from math import ceil
from pathlib import Path
from random import random
from typing import Dict, List, Union
CWD = Path(__file__).parent.as_posix()
INPUTS_DIR = f"{CWD}/inputs"
OUTPUTS_DIR = f"{CWD}/outputs"


# from hypothesis.strategies import composite
# import hypothesis.strategies as st
# from datetime import datetime, timedelta

# results_status_vals = ["Incomplete", "Complete", "Failed"]

# user_browser_vals = ["Chrome", "IE", "Firefox", "Safari", "Other"]

# user_device_vals = ["Desktop", "Mobile", "Tablet", "Other"]

# user_os_vals = [
#     "Windows (deprecated)",
#     "Linux (deprecated)",
#     "MacOS (deprecated)",
#     "iOS (deprecated)",
#     "Android (deprecated)",
#     "Other (deprecated)",
# ]


# @composite
# def form_items(draw, keys = {}):
#     ...

# @composite
# def form_result(draw, keys = {}):
#     isofmt = lambda d: datetime.isoformat(d) + "Z"
#     dt = st.datetimes(allow_imaginary=False)
#     off = timedelta(hours=random())
#     return draw(
#         st.fixed_dictionaries(
#             {
#                 "user_ip": st.ip_addresses(v=4).map(str),
#                 "user_referrer": st.sampled_from(["N/A", "example.com"]),
#                 "user_os": st.sampled_from(user_os_vals),
#                 "login_email": st.emails() | st.none(),
#                 "date_start": st.shared(dt, key="d").map(isofmt),
#                 "date_finish": st.shared(dt, key="d").map(lambda d: d + off).map(isofmt),
#                 "date_update": st.shared(dt, key="d").map(lambda d: d + off).map(isofmt),
#                 "login_username": st.text() | st.none(),
#                 "user_device": st.sampled_from(user_device_vals),
#                 "result_status": st.sampled_from(results_status_vals),
#                 "user_browser": st.sampled_from(user_browser_vals),
#                 "id": st.integers(min_value=0),  # todo
#                 "items": form_items(keys = keys),
#             }
#         )
#     )


# @composite
# def form_page(draw, num_results: int = 10):
#     return draw(st.lists(form_result(), min_size=num_results, max_size=num_results))

# @composite
# def results_records(draw, num_results: int = 500, num_pages: int = 1):
#     ...

def load_json(path: str) -> dict:
    with open(path, "r", encoding='utf-8') as fp:
        return json.load(fp)


def create_example_results(n: int, page_sz: int = 500) -> dict:
    """Create n example formsite results with all possible controls"""

    pages: List[Dict[str, Union[str, int]]] = [{} for _ in range(ceil(n / 500))]
    page: List[Dict[str, Union[str, int]]] = []
    for i in range(n):
        result_template = {
            "user_ip": "IP_ADDR",
            "user_referrer": "N/A",
            "user_os": "Windows (deprecated)",
            "login_email": "",
            "date_update": "2021-01-01T00:00:00Z",
            "login_username": "",
            "user_device": "Desktop",
            "date_start": "2021-01-01T00:00:00Z",
            "result_status": "Complete",
            "date_finish": "2021-01-01T00:00:00Z",
            "user_browser": "Firefox",
            "id": i,
            "items": [
                {"id": "320", "position": 2, "value": "email@example.com"},
                {
                    "values": [{"position": 0, "value": "Value1"}],
                    "id": "306",
                    "position": 3,
                },
                {
                    "values": [{"position": 0, "value": "Choice A"}],
                    "id": "318",
                    "position": 4,
                },
                {
                    "values": [
                        {
                            "other": "Other as well",
                            "position": 1,
                            "value": "Choice B",
                        }
                    ],
                    "id": "319",
                    "position": 5,
                },
                {"id": "321", "position": 6, "value": "Short answer"},
                {"id": "322", "position": 7, "value": "Loooooooooooooong answer"},
                {"id": "323", "position": 8, "value": "2008-08-13"},
                {"id": "324", "position": 9, "value": "5.00"},
                {"id": "329", "position": 10, "value": "25.00"},
                {"id": "325", "position": 11, "value": "4791974664436467"},
                {
                    "values": [
                        {"position": 0, "value": "example_url1"},
                        {"position": 1, "value": "example_url2"},
                    ],
                    "id": "326",
                    "position": 12,
                },
                {"id": "327", "position": 13, "value": "example_signature"},
                {"id": "328-0", "position": 14, "value": "I am listing answers"},
                {"id": "328-1", "position": 14, "value": "One "},
                {"id": "328-2", "position": 14, "value": "Two"},
                {"id": "330", "position": 15, "value": ""},
                {"id": "331-0", "position": 16, "value": "3"},
                {"id": "331-1", "position": 16, "value": "2"},
                {"id": "331-2", "position": 16, "value": "1"},
                {"id": "332-0", "position": 17, "value": "12"},
                {"id": "332-1", "position": 17, "value": "44"},
                {"id": "332-2", "position": 17, "value": "44"},
                {"id": "333", "position": 18, "value": "65"},
                {"id": "334", "position": 19, "value": "4"},
                {
                    "values": [{"position": 0, "value": "chosen"}],
                    "id": "285",
                    "position": 20,
                },
                {
                    "values": [{"position": 0, "value": "Choice A"}],
                    "id": "345",
                    "position": 21,
                },
                {
                    "values": [
                        {"position": 0, "value": "Choice A"},
                        {"position": 1, "value": "Choice B"},
                    ],
                    "id": "347",
                    "position": 22,
                },
                {
                    "values": [{"position": 0, "value": "Choice A"}],
                    "id": "346",
                    "position": 23,
                },
                {
                    "values": [
                        {"position": 0, "value": "Choice A"},
                        {"other": "ALL", "position": 1, "value": "Choice B"},
                    ],
                    "id": "301",
                    "position": 24,
                },
                {
                    "values": [{"position": 0, "value": "C"}],
                    "id": "348-0",
                    "position": 25,
                },
                {
                    "values": [{"position": 1, "value": "D"}],
                    "id": "348-1",
                    "position": 25,
                },
                {
                    "values": [{"position": 2, "value": "A3"}],
                    "id": "349-0-0",
                    "position": 26,
                },
                {
                    "values": [{"position": 2, "value": "A3"}],
                    "id": "349-0-1",
                    "position": 26,
                },
                {
                    "values": [{"position": 2, "value": "A3"}],
                    "id": "349-0-2",
                    "position": 26,
                },
                {
                    "values": [{"position": 2, "value": "A3"}],
                    "id": "349-0-3",
                    "position": 26,
                },
                {
                    "values": [{"position": 1, "value": "B2"}],
                    "id": "349-1-0",
                    "position": 26,
                },
                {
                    "values": [{"position": 1, "value": "B2"}],
                    "id": "349-1-1",
                    "position": 26,
                },
                {
                    "values": [{"position": 0, "value": "B1"}],
                    "id": "349-1-2",
                    "position": 26,
                },
                {
                    "values": [{"position": 0, "value": "B1"}],
                    "id": "349-1-3",
                    "position": 26,
                },
                {
                    "values": [{"position": 2, "value": "C3"}],
                    "id": "349-2-0",
                    "position": 26,
                },
                {
                    "values": [{"position": 0, "value": "C1"}],
                    "id": "349-2-1",
                    "position": 26,
                },
                {
                    "values": [{"position": 0, "value": "C1"}],
                    "id": "349-2-2",
                    "position": 26,
                },
                {
                    "values": [{"position": 1, "value": "C2"}],
                    "id": "349-2-3",
                    "position": 26,
                },
                {
                    "values": [{"position": 1, "value": "D2"}],
                    "id": "349-3-0",
                    "position": 26,
                },
                {
                    "values": [{"position": 0, "value": "D1"}],
                    "id": "349-3-1",
                    "position": 26,
                },
                {
                    "values": [{"position": 2, "value": "D3"}],
                    "id": "349-3-2",
                    "position": 26,
                },
                {
                    "values": [{"position": 1, "value": "D2"}],
                    "id": "349-3-3",
                    "position": 26,
                },
                {
                    "values": [{"position": 0, "value": "B1"}],
                    "id": "350-0",
                    "position": 27,
                },
                {
                    "values": [{"position": 1, "value": "B2"}],
                    "id": "350-1",
                    "position": 27,
                },
                {
                    "values": [{"position": 0, "value": "B1"}],
                    "id": "350-2",
                    "position": 27,
                },
                {
                    "values": [{"position": 0, "value": "A1"}],
                    "id": "351-0-0",
                    "position": 28,
                },
                {
                    "values": [{"position": 1, "value": "A2"}],
                    "id": "351-0-1",
                    "position": 28,
                },
                {
                    "values": [{"position": 0, "value": "B1"}],
                    "id": "351-1-0",
                    "position": 28,
                },
                {
                    "values": [{"position": 1, "value": "B2"}],
                    "id": "351-1-1",
                    "position": 28,
                },
                {
                    "values": [{"position": 0, "value": "C1"}],
                    "id": "351-2-0",
                    "position": 28,
                },
                {
                    "values": [{"position": 1, "value": "C2"}],
                    "id": "351-2-1",
                    "position": 28,
                },
                {
                    "values": [{"position": 0, "value": "D1"}],
                    "id": "351-3-0",
                    "position": 28,
                },
                {
                    "values": [{"position": 1, "value": "D2"}],
                    "id": "351-3-1",
                    "position": 28,
                },
                {
                    "values": [
                        {"position": 0, "value": "Choice A"},
                        {"position": 1, "value": "Choice B"},
                        {"position": 2, "value": "Choice C"},
                        {"position": 3, "value": "Choice D"},
                        {"position": 4, "value": "Choice E"},
                        {"position": 5, "value": "Choice F"},
                    ],
                    "id": "352-0",
                    "position": 29,
                },
                {
                    "values": [
                        {"position": 1, "value": "Choice B"},
                        {"position": 5, "value": "Choice F"},
                    ],
                    "id": "352-1",
                    "position": 29,
                },
                {
                    "values": [
                        {"position": 2, "value": "Choice C"},
                        {"position": 4, "value": "Choice E"},
                    ],
                    "id": "352-2",
                    "position": 29,
                },
                {
                    "values": [{"position": 3, "value": "Choice D"}],
                    "id": "352-3",
                    "position": 29,
                },
                {
                    "values": [{"position": 0, "value": "A1"}],
                    "id": "353-0-0",
                    "position": 30,
                },
                {
                    "values": [{"position": 0, "value": "B1"}],
                    "id": "353-1-0",
                    "position": 30,
                },
                {
                    "values": [{"position": 0, "value": "C1"}],
                    "id": "353-2-0",
                    "position": 30,
                },
                {
                    "values": [{"position": 0, "value": "D1"}],
                    "id": "353-3-0",
                    "position": 30,
                },
                {
                    "values": [
                        {"position": 0, "value": "a"},
                        {"position": 1, "value": "b"},
                        {"position": 2, "value": "c"},
                    ],
                    "id": "354-0",
                    "position": 31,
                },
                {
                    "values": [
                        {"position": 0, "value": "d"},
                        {"position": 1, "value": "e"},
                        {"position": 2, "value": "f"},
                    ],
                    "id": "354-1",
                    "position": 31,
                },
                {
                    "values": [
                        {"position": 0, "value": "g"},
                        {"position": 1, "value": "h"},
                        {"position": 2, "value": "i"},
                    ],
                    "id": "354-2",
                    "position": 31,
                },
                {
                    "values": [
                        {"position": 0, "value": "1"},
                        {"position": 1, "value": "2"},
                    ],
                    "id": "355-0",
                    "position": 32,
                },
                {
                    "values": [
                        {"position": 0, "value": "3"},
                        {"position": 1, "value": ""},
                    ],
                    "id": "355-1",
                    "position": 32,
                },
                {
                    "values": [{"position": 3, "value": "4"}],
                    "id": "356-0",
                    "position": 33,
                },
                {
                    "values": [{"position": 11, "value": "12"}],
                    "id": "356-1",
                    "position": 33,
                },
                {
                    "values": [{"position": 4, "value": "5"}],
                    "id": "356-2",
                    "position": 33,
                },
                {
                    "values": [{"position": 1, "value": "2"}],
                    "id": "356-3",
                    "position": 33,
                },
            ],
        }
        # ----
        if len(page) < page_sz:
            page.append(result_template)
        else:
            pages[n // page_sz] = {"results": page.copy()}
            page = []
    if len(page) > 0:
        pages[-1] = {"results": page.copy()}
    return pages


def create_example_items() -> dict:
    """Create an example formsite item with all possible controls"""
    item_template = {
        "items": [
            {"id": "320", "position": 2, "label": "email_address"},
            {"id": "306", "position": 3, "label": "dropdown"},
            {"id": "318", "position": 4, "label": "radio"},
            {"id": "319", "position": 5, "label": "radio_w_other"},
            {"id": "321", "position": 6, "label": "short_answer"},
            {"id": "322", "position": 7, "label": "long_answer"},
            {"id": "323", "position": 8, "label": "calendar"},
            {"id": "324", "position": 9, "label": "number"},
            {"id": "329", "position": 10, "label": "calculation_number_squared"},
            {"id": "325", "position": 11, "label": "credit_card"},
            {"id": "326", "position": 12, "label": "file_upload"},
            {"id": "327", "position": 13, "label": "signature"},
            {
                "children": ["328-0", "328-1", "328-2"],
                "id": "328",
                "position": 14,
                "label": "short_answer_list",
            },
            {"id": "328-0", "position": 14, "label": "1"},
            {"id": "328-1", "position": 14, "label": "2"},
            {"id": "328-2", "position": 14, "label": "3"},
            {"id": "330", "position": 15, "label": "hidden_value"},
            {
                "children": ["331-0", "331-1", "331-2"],
                "id": "331",
                "position": 16,
                "label": "ranking",
            },
            {"id": "331-0", "position": 16, "label": "Choice 1"},
            {"id": "331-1", "position": 16, "label": "Choice 2"},
            {"id": "331-2", "position": 16, "label": "Choice 3"},
            {
                "children": ["332-0", "332-1", "332-2"],
                "id": "332",
                "position": 17,
                "label": "rating",
            },
            {"id": "332-0", "position": 17, "label": "Choice 1"},
            {"id": "332-1", "position": 17, "label": "Choice 2"},
            {"id": "332-2", "position": 17, "label": "Choice 3"},
            {"id": "333", "position": 18, "label": "slider"},
            {"id": "334", "position": 19, "label": "number_scale"},
            {"id": "285", "position": 20, "label": "checkbox_single"},
            {"id": "345", "position": 21, "label": "email_radial"},
            {"id": "347", "position": 22, "label": "email_checkbox"},
            {"id": "346", "position": 23, "label": "email_dropdown"},
            {"id": "301", "position": 24, "label": "checkbox_multiple"},
            {
                "children": ["348-0", "348-1"],
                "id": "348",
                "position": 25,
                "label": "matrix_radio (payoff matrix)",
            },
            {"id": "348-0", "position": 25, "label": "A"},
            {"id": "348-1", "position": 25, "label": "B"},
            {
                "children": ["349-0", "349-1", "349-2", "349-3"],
                "id": "349",
                "position": 26,
                "label": "matrix_radio_multi",
            },
            {
                "children": ["349-0-0", "349-0-1", "349-0-2", "349-0-3"],
                "id": "349-0",
                "position": 26,
                "label": "A",
            },
            {"id": "349-0-0", "position": 26, "label": "Subquestion 1"},
            {"id": "349-0-1", "position": 26, "label": "Subquestion 2"},
            {"id": "349-0-2", "position": 26, "label": "Subquestion 3"},
            {"id": "349-0-3", "position": 26, "label": "Subquestion 4"},
            {
                "children": ["349-1-0", "349-1-1", "349-1-2", "349-1-3"],
                "id": "349-1",
                "position": 26,
                "label": "B",
            },
            {"id": "349-1-0", "position": 26, "label": "Subquestion 1"},
            {"id": "349-1-1", "position": 26, "label": "Subquestion 2"},
            {"id": "349-1-2", "position": 26, "label": "Subquestion 3"},
            {"id": "349-1-3", "position": 26, "label": "Subquestion 4"},
            {
                "children": ["349-2-0", "349-2-1", "349-2-2", "349-2-3"],
                "id": "349-2",
                "position": 26,
                "label": "C",
            },
            {"id": "349-2-0", "position": 26, "label": "Subquestion 1"},
            {"id": "349-2-1", "position": 26, "label": "Subquestion 2"},
            {"id": "349-2-2", "position": 26, "label": "Subquestion 3"},
            {"id": "349-2-3", "position": 26, "label": "Subquestion 4"},
            {
                "children": ["349-3-0", "349-3-1", "349-3-2", "349-3-3"],
                "id": "349-3",
                "position": 26,
                "label": "D",
            },
            {"id": "349-3-0", "position": 26, "label": "Subquestion 1"},
            {"id": "349-3-1", "position": 26, "label": "Subquestion 2"},
            {"id": "349-3-2", "position": 26, "label": "Subquestion 3"},
            {"id": "349-3-3", "position": 26, "label": "Subquestion 4"},
            {
                "children": ["350-0", "350-1", "350-2"],
                "id": "350",
                "position": 27,
                "label": "matrix_dropdown",
            },
            {"id": "350-0", "position": 27, "label": "A1"},
            {"id": "350-1", "position": 27, "label": "A2"},
            {"id": "350-2", "position": 27, "label": "A3"},
            {
                "children": ["351-0", "351-1", "351-2", "351-3"],
                "id": "351",
                "position": 28,
                "label": "matrix_dropdown_multi",
            },
            {
                "children": ["351-0-0", "351-0-1"],
                "id": "351-0",
                "position": 28,
                "label": "A",
            },
            {"id": "351-0-0", "position": 28, "label": "Subquestion 1"},
            {"id": "351-0-1", "position": 28, "label": "Subquestion 2"},
            {
                "children": ["351-1-0", "351-1-1"],
                "id": "351-1",
                "position": 28,
                "label": "B",
            },
            {"id": "351-1-0", "position": 28, "label": "Subquestion 1"},
            {"id": "351-1-1", "position": 28, "label": "Subquestion 2"},
            {
                "children": ["351-2-0", "351-2-1"],
                "id": "351-2",
                "position": 28,
                "label": "C",
            },
            {"id": "351-2-0", "position": 28, "label": "Subquestion 1"},
            {"id": "351-2-1", "position": 28, "label": "Subquestion 2"},
            {
                "children": ["351-3-0", "351-3-1"],
                "id": "351-3",
                "position": 28,
                "label": "D",
            },
            {"id": "351-3-0", "position": 28, "label": "Subquestion 1"},
            {"id": "351-3-1", "position": 28, "label": "Subquestion 2"},
            {
                "children": ["352-0", "352-1", "352-2", "352-3"],
                "id": "352",
                "position": 29,
                "label": "matrix_checkbox",
            },
            {"id": "352-0", "position": 29, "label": "Item 1"},
            {"id": "352-1", "position": 29, "label": "Item 2"},
            {"id": "352-2", "position": 29, "label": "Item 3"},
            {"id": "352-3", "position": 29, "label": "Item 4"},
            {
                "children": ["353-0", "353-1", "353-2", "353-3"],
                "id": "353",
                "position": 30,
                "label": "matrix_checkbox_multi",
            },
            {"children": ["353-0-0"], "id": "353-0", "position": 30, "label": "A"},
            {"id": "353-0-0", "position": 30, "label": "item"},
            {"children": ["353-1-0"], "id": "353-1", "position": 30, "label": "B"},
            {"id": "353-1-0", "position": 30, "label": "item"},
            {"children": ["353-2-0"], "id": "353-2", "position": 30, "label": "C"},
            {"id": "353-2-0", "position": 30, "label": "item"},
            {"children": ["353-3-0"], "id": "353-3", "position": 30, "label": "D"},
            {"id": "353-3-0", "position": 30, "label": "item"},
            {
                "children": ["354-0", "354-1", "354-2"],
                "id": "354",
                "position": 31,
                "label": "matrix_short_answer",
            },
            {"id": "354-0", "position": 31, "label": "Row1"},
            {"id": "354-1", "position": 31, "label": "Row2"},
            {"id": "354-2", "position": 31, "label": "Row3"},
            {
                "children": ["355-0", "355-1"],
                "id": "355",
                "position": 32,
                "label": "matrix_long_answer",
            },
            {"id": "355-0", "position": 32, "label": "L1"},
            {"id": "355-1", "position": 32, "label": "L2"},
            {
                "children": ["356-0", "356-1", "356-2", "356-3"],
                "id": "356",
                "position": 33,
                "label": "matrix_star",
            },
            {"id": "356-0", "position": 33, "label": "Choice 1"},
            {"id": "356-1", "position": 33, "label": "Choice 2"},
            {"id": "356-2", "position": 33, "label": "Choice 3"},
            {"id": "356-3", "position": 33, "label": "Choice 3"},
        ]
    }

    return item_template
