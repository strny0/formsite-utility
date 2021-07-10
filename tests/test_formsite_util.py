import os 
from datetime import datetime as dt
from datetime import timedelta as td
from typing import Any, List, Set, Tuple
import shutil
import pandas as pd
from formsite_util.core import FormsiteCredentials, FormsiteInterface, FormsiteParams
from formsite_util.downloader import _FormsiteDownloader

def init_form(form_id: str, timezone:str='America/Chicago') -> FormsiteInterface:
    day_offset = float(os.getenv('days_back'))
    date = dt.now()-td(days=day_offset)
    auth = FormsiteCredentials(os.getenv('token'), os.getenv('server'), os.getenv('directory'))
    params = FormsiteParams(afterdate=date.strftime("%Y-%m-%d"), timezone=timezone)
    return FormsiteInterface(form_id, auth, params=params)

def assert_fetch(interface: FormsiteInterface) -> Tuple[str, List[str]]:
    items, results = interface._perform_api_fetch(False, False)

    assert isinstance(items, str)
    assert len(items) > 0

    assert isinstance(results, list)
    assert len(results) > 0

    return items, results

def check_if_is_date(date: Any) -> Any:
    assert isinstance(date, dt)
    return date

def assert_processing(items: str, results: List[str], interface: FormsiteInterface) -> pd.DataFrame:
    dataframe = interface._assemble_dataframe(items, results)

    assert dataframe.shape[1] > 0
    assert dataframe.shape[0] > 0
    assert "Reference #" in dataframe.columns
    assert "Status" in dataframe.columns
    assert "Date" in dataframe.columns
    assert "Start Time" in dataframe.columns
    assert "Finish Time" in dataframe.columns
    assert "Duration (s)" in dataframe.columns
    assert "User" in dataframe.columns
    assert "Browser" in dataframe.columns
    assert "Device" in dataframe.columns
    assert "Referrer" in dataframe.columns

    dataframe['Date'].apply(lambda date: check_if_is_date(date))
    dataframe['Start Time'].apply(lambda date: check_if_is_date(date))
    dataframe['Finish Time'].apply(lambda date: check_if_is_date(date))

    return dataframe

def assert_links(interface: FormsiteInterface) -> Set[str]:
    links = interface.ReturnLinks()
    
    assert isinstance(links, set)
    for i in interface.ReturnLinks(links_regex=r'^.+\.jpg$'):
        assert i.lower().endswith('.jpg')
    
    return links

def assert_downloads(interface: FormsiteInterface) -> None:
    test_dir = os.getenv('test_download')
    while len(interface.Links) > int(os.getenv('max_downloads')):
        interface.Links.pop()

    interface.DownloadFiles(download_folder=test_dir, overwrite_existing=False)
    example_url = interface.Links.pop()
    interface.Links.add(example_url)
    url = example_url.rsplit('/', 1)[0] +'/'
    download_handler = _FormsiteDownloader(test_dir, interface.Links)
    downloaded_links = download_handler._list_files_in_download_dir(url)
    for link in interface.Links:
        assert link in downloaded_links
    shutil.rmtree(test_dir)
    
def do_tests(form_id: str) -> None:
    interface = init_form(form_id)
    items, results = assert_fetch(interface)
    interface.Data = assert_processing(items, results, interface)
    interface.Links = assert_links(interface)
    assert_downloads(interface)
    del interface

def test_form1():
    do_tests(os.getenv('form1'))

def test_form2():
    do_tests(os.getenv('form2'))

def test_form3():
    do_tests(os.getenv('form3'))

def test_form4():
    do_tests(os.getenv('form4'))

def test_form5():
    do_tests(os.getenv('form5'))
