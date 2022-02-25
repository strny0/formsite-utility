import json
import pandas as pd
from tests.util import (
    create_example_items,
    INPUTS_DIR,
    OUTPUTS_DIR,
    create_example_results,
)
from formsite_util.cache import (
    items_load,
    items_match_data,
    items_save,
    results_load,
    results_save,
)
from formsite_util.form_parser import FormParser


def test_items_match_data_exact():
    items = create_example_items()
    parser = FormParser()
    results_raw = create_example_results(10)
    _ = [parser.feed(c) for c in results_raw]
    df = parser.as_dataframe()
    assert items_match_data(items, df.columns) is True


def test_items_match_data_inexact():
    items = create_example_items()
    items["items"].append({"id": "123131"})  # add extra item
    parser = FormParser()
    results_raw = create_example_results(10)
    _ = [parser.feed(c) for c in results_raw]
    df = parser.as_dataframe()
    assert items_match_data(items, df.columns) is True


def test_items_match_data_false():
    items = {"items": []}
    parser = FormParser()
    results_raw = create_example_results(10)
    _ = [parser.feed(c) for c in results_raw]
    df = parser.as_dataframe()
    assert items_match_data(items, df.columns) is False


def test_items_save_load():
    created = create_example_items()
    items_save(created, f"{OUTPUTS_DIR}/cache_items.json")
    loaded = items_load(f"{OUTPUTS_DIR}/cache_items.json")
    assert created == loaded


def test_items_load():
    created = create_example_items()
    loaded = items_load(f"{INPUTS_DIR}/cache_items.json")
    assert created == loaded


def test_items_save():
    created = create_example_items()
    items_save(created, f"{OUTPUTS_DIR}/cache_items.json")
    with open(f"{OUTPUTS_DIR}/cache_items.json", "r", encoding="utf-8") as fp:
        loaded = json.load(fp)
    assert created == loaded


def test_results_save_load_parquet():
    path = f"{OUTPUTS_DIR}/cache_results.parquet"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_parquet():
    path = f"{OUTPUTS_DIR}/cache_results.parquet"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = pd.read_parquet(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_load_parquet():
    path = f"{INPUTS_DIR}/cache_results.parquet"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_load_feather():
    path = f"{OUTPUTS_DIR}/cache_results.feather"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_feather():
    path = f"{OUTPUTS_DIR}/cache_results.feather"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = pd.read_feather(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_load_feather():
    path = f"{INPUTS_DIR}/cache_results.feather"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_load_pickle():
    path = f"{OUTPUTS_DIR}/cache_results.pickle"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_pickle():
    path = f"{OUTPUTS_DIR}/cache_results.pickle"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = pd.read_pickle(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_load_pickle():
    path = f"{INPUTS_DIR}/cache_results.pickle"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_load_pkl():
    path = f"{OUTPUTS_DIR}/cache_results.pkl"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_pkl():
    path = f"{OUTPUTS_DIR}/cache_results.pkl"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = pd.read_pickle(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_load_pkl():
    path = f"{INPUTS_DIR}/cache_results.pkl"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_load_hdf():
    path = f"{OUTPUTS_DIR}/cache_results.hdf"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)


def test_results_save_hdf():
    path = f"{OUTPUTS_DIR}/cache_results.hdf"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    results_save(df1, path)
    df2 = pd.read_hdf(path, key="data")
    assert pd.DataFrame.equals(df1, df2)


def test_results_load_hdf():
    path = f"{INPUTS_DIR}/cache_results.hdf"
    parser = FormParser()
    created = create_example_results(10)
    _ = [parser.feed(c) for c in created]
    df1 = parser.as_dataframe()
    df2 = results_load(path)
    assert pd.DataFrame.equals(df1, df2)
