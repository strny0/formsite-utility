import json
import pandas as pd
from formsite_util._form_parser import FormParser
from tests.util import create_example_results, create_example_items, INPUTS_DIR


CACHED_RESULT = {
    "result_status": "Complete",
    "login_username": "",
    "login_email": "",
    "320": "email@example.com",
    "306": "Value1",
    "318": "Choice A",
    "319": "Choice B",
    "321": "Short answer",
    "322": "Loooooooooooooong answer",
    "323": "2008-08-13",
    "324": "5.00",
    "329": "25.00",
    "325": "4791974664436467",
    "326": "example_url1 | example_url2",
    "327": "example_signature",
    "328-0": "I am listing answers",
    "328-1": "One ",
    "328-2": "Two",
    "330": "",
    "331-0": "3",
    "331-1": "2",
    "331-2": "1",
    "332-0": "12",
    "332-1": "44",
    "332-2": "44",
    "333": "65",
    "334": "4",
    "285": "chosen",
    "345": "Choice A",
    "347": "Choice A | Choice B",
    "346": "Choice A",
    "301": "Choice A | Choice B",
    "348-0": "C",
    "348-1": "D",
    "349-0": "A3 | B2 | C3 | D2",
    "349-1": "A3 | B2 | C1 | D1",
    "349-2": "A3 | B1 | C1 | D3",
    "349-3": "A3 | B1 | C2 | D2",
    "350-0": "B1",
    "350-1": "B2",
    "350-2": "B1",
    "351-0": "A1 | B1 | C1 | D1",
    "351-1": "A2 | B2 | C2 | D2",
    "352-0": "Choice A | Choice B | Choice C | Choice D | Choice E | Choice F",
    "352-1": "Choice B | Choice F",
    "352-2": "Choice C | Choice E",
    "352-3": "Choice D",
    "353-0": "A1 | B1 | C1 | D1",
    "354-0": "a | b | c",
    "354-1": "d | e | f",
    "354-2": "g | h | i",
    "355-0": "1 | 2",
    "355-1": "3 | ",
    "356-0": "4",
    "356-1": "12",
    "356-2": "5",
    "356-3": "2",
    "date_update": "2021-01-01T00:00:00Z",
    "date_start": "2021-01-01T00:00:00Z",
    "date_finish": "2021-01-01T00:00:00Z",
    "user_ip": "IP_ADDR",
    "user_browser": "Firefox",
    "user_device": "Desktop",
    "user_referrer": "N/A",
}

CACHED_RESULT_ITEMS = [
    {"id": "320", "position": 2, "value": "email@example.com"},
    {"values": [{"position": 0, "value": "Value1"}], "id": "306", "position": 3},
    {"values": [{"position": 0, "value": "Choice A"}], "id": "318", "position": 4},
    {
        "values": [{"other": "Other as well", "position": 1, "value": "Choice B"}],
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
    {"values": [{"position": 0, "value": "chosen"}], "id": "285", "position": 20},
    {"values": [{"position": 0, "value": "Choice A"}], "id": "345", "position": 21},
    {
        "values": [
            {"position": 0, "value": "Choice A"},
            {"position": 1, "value": "Choice B"},
        ],
        "id": "347",
        "position": 22,
    },
    {"values": [{"position": 0, "value": "Choice A"}], "id": "346", "position": 23},
    {
        "values": [
            {"position": 0, "value": "Choice A"},
            {"other": "ALL", "position": 1, "value": "Choice B"},
        ],
        "id": "301",
        "position": 24,
    },
    {"values": [{"position": 0, "value": "C"}], "id": "348-0", "position": 25},
    {"values": [{"position": 1, "value": "D"}], "id": "348-1", "position": 25},
    {"values": [{"position": 2, "value": "A3"}], "id": "349-0-0", "position": 26},
    {"values": [{"position": 2, "value": "A3"}], "id": "349-0-1", "position": 26},
    {"values": [{"position": 2, "value": "A3"}], "id": "349-0-2", "position": 26},
    {"values": [{"position": 2, "value": "A3"}], "id": "349-0-3", "position": 26},
    {"values": [{"position": 1, "value": "B2"}], "id": "349-1-0", "position": 26},
    {"values": [{"position": 1, "value": "B2"}], "id": "349-1-1", "position": 26},
    {"values": [{"position": 0, "value": "B1"}], "id": "349-1-2", "position": 26},
    {"values": [{"position": 0, "value": "B1"}], "id": "349-1-3", "position": 26},
    {"values": [{"position": 2, "value": "C3"}], "id": "349-2-0", "position": 26},
    {"values": [{"position": 0, "value": "C1"}], "id": "349-2-1", "position": 26},
    {"values": [{"position": 0, "value": "C1"}], "id": "349-2-2", "position": 26},
    {"values": [{"position": 1, "value": "C2"}], "id": "349-2-3", "position": 26},
    {"values": [{"position": 1, "value": "D2"}], "id": "349-3-0", "position": 26},
    {"values": [{"position": 0, "value": "D1"}], "id": "349-3-1", "position": 26},
    {"values": [{"position": 2, "value": "D3"}], "id": "349-3-2", "position": 26},
    {"values": [{"position": 1, "value": "D2"}], "id": "349-3-3", "position": 26},
    {"values": [{"position": 0, "value": "B1"}], "id": "350-0", "position": 27},
    {"values": [{"position": 1, "value": "B2"}], "id": "350-1", "position": 27},
    {"values": [{"position": 0, "value": "B1"}], "id": "350-2", "position": 27},
    {"values": [{"position": 0, "value": "A1"}], "id": "351-0-0", "position": 28},
    {"values": [{"position": 1, "value": "A2"}], "id": "351-0-1", "position": 28},
    {"values": [{"position": 0, "value": "B1"}], "id": "351-1-0", "position": 28},
    {"values": [{"position": 1, "value": "B2"}], "id": "351-1-1", "position": 28},
    {"values": [{"position": 0, "value": "C1"}], "id": "351-2-0", "position": 28},
    {"values": [{"position": 1, "value": "C2"}], "id": "351-2-1", "position": 28},
    {"values": [{"position": 0, "value": "D1"}], "id": "351-3-0", "position": 28},
    {"values": [{"position": 1, "value": "D2"}], "id": "351-3-1", "position": 28},
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
    {"values": [{"position": 3, "value": "Choice D"}], "id": "352-3", "position": 29},
    {"values": [{"position": 0, "value": "A1"}], "id": "353-0-0", "position": 30},
    {"values": [{"position": 0, "value": "B1"}], "id": "353-1-0", "position": 30},
    {"values": [{"position": 0, "value": "C1"}], "id": "353-2-0", "position": 30},
    {"values": [{"position": 0, "value": "D1"}], "id": "353-3-0", "position": 30},
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
        "values": [{"position": 0, "value": "1"}, {"position": 1, "value": "2"}],
        "id": "355-0",
        "position": 32,
    },
    {
        "values": [{"position": 0, "value": "3"}, {"position": 1, "value": ""}],
        "id": "355-1",
        "position": 32,
    },
    {"values": [{"position": 3, "value": "4"}], "id": "356-0", "position": 33},
    {"values": [{"position": 11, "value": "12"}], "id": "356-1", "position": 33},
    {"values": [{"position": 4, "value": "5"}], "id": "356-2", "position": 33},
    {"values": [{"position": 1, "value": "2"}], "id": "356-3", "position": 33},
]

CACHED_RESULT_ITEMS_PARSED = {
    "320": "email@example.com",
    "306": "Value1",
    "318": "Choice A",
    "319": "Choice B",
    "321": "Short answer",
    "322": "Loooooooooooooong answer",
    "323": "2008-08-13",
    "324": "5.00",
    "329": "25.00",
    "325": "4791974664436467",
    "326": "example_url1 | example_url2",
    "327": "example_signature",
    "328-0": "I am listing answers",
    "328-1": "One ",
    "328-2": "Two",
    "330": "",
    "331-0": "3",
    "331-1": "2",
    "331-2": "1",
    "332-0": "12",
    "332-1": "44",
    "332-2": "44",
    "333": "65",
    "334": "4",
    "285": "chosen",
    "345": "Choice A",
    "347": "Choice A | Choice B",
    "346": "Choice A",
    "301": "Choice A | Choice B",
    "348-0": "C",
    "348-1": "D",
    "349-0": "A3 | B2 | C3 | D2",
    "349-1": "A3 | B2 | C1 | D1",
    "349-2": "A3 | B1 | C1 | D3",
    "349-3": "A3 | B1 | C2 | D2",
    "350-0": "B1",
    "350-1": "B2",
    "350-2": "B1",
    "351-0": "A1 | B1 | C1 | D1",
    "351-1": "A2 | B2 | C2 | D2",
    "352-0": "Choice A | Choice B | Choice C | Choice D | Choice E | Choice F",
    "352-1": "Choice B | Choice F",
    "352-2": "Choice C | Choice E",
    "352-3": "Choice D",
    "353-0": "A1 | B1 | C1 | D1",
    "354-0": "a | b | c",
    "354-1": "d | e | f",
    "354-2": "g | h | i",
    "355-0": "1 | 2",
    "355-1": "3 | ",
    "356-0": "4",
    "356-1": "12",
    "356-2": "5",
    "356-3": "2",
}


def prepare_parser(n: int = 10) -> FormParser:
    parser = FormParser()
    _ = [parser.feed(r) for r in create_example_results(n)]
    return parser


def test_parser_feed():
    """Confirm parser feed correctly parses data"""
    parser = FormParser()
    _ = [parser.feed(r) for r in create_example_results(500)]
    assert len(parser.data) == 500
    for i in range(500):
        assert parser.data[i]["id"] == i  # test no data was lost
        for k, v in parser.data[i].items():
            if k == "id":
                continue
            assert CACHED_RESULT.get(k) == v


def test_parse_results_items():
    assert CACHED_RESULT_ITEMS_PARSED == FormParser().parse_results_items(
        CACHED_RESULT_ITEMS
    )


def test_parser_as_dataframe():
    parser = prepare_parser()
    saved_df = pd.read_parquet(f"{INPUTS_DIR}/as_dataframe_input.parquet")
    assert parser.as_dataframe().equals(saved_df)


def test_parser_as_records():
    parser = prepare_parser()
    with open(f"{INPUTS_DIR}/as_records_input.json", "r", encoding="utf-8") as fp:
        saved_records = json.load(fp)
    assert parser.as_records() == saved_records


def test_parser_rename_map():
    items = create_example_items()
    rename_map = FormParser.create_rename_map(items)
    with open(f"{INPUTS_DIR}/rename_map.json", "r", encoding="utf-8") as fp:
        saved_rename_map = json.load(fp)
    assert rename_map == saved_rename_map
