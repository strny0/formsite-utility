from formsite_util import FormData
from tests.util import load_json, INPUTS_DIR

import pandas as pd


def test_FormData_constructor_path():
    res = f"{INPUTS_DIR}/cache_results.feather"
    itm = f"{INPUTS_DIR}/cache_items.json"
    form = FormData(res, itm)
    results = pd.read_feather(res)
    items = load_json(itm)
    assert form.results.equals(results)
    assert form.items == items


def test_FormData_constructor_pandas():
    res = f"{INPUTS_DIR}/cache_results.feather"
    itm = f"{INPUTS_DIR}/cache_items.json"
    results = pd.read_feather(res)
    items = load_json(itm)
    form = FormData(results, items)
    assert form.results.equals(results)
    assert form.items == items
