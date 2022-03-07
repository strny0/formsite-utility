<!-- HEADER -->
<br />
<p align="center">
  <a>
    <img src="https://www.formsite.com/wp-content/themes/formsite-theme/assets/favicon/favicon-96x96.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Formsite Utility</h3>
</p>

Python library and CLI tool for interacing with the FormSite API

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/31145f1b97934080981a53783803701f)](https://www.codacy.com/gh/strny0/formsite-utility/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=strny0/formsite-utility&amp;utm_campaign=Badge_Grade)
[![PyPI version](https://badge.fury.io/py/formsite-util.svg)](https://badge.fury.io/py/formsite-util)
![PyPI - Downloads](https://img.shields.io/pypi/dm/formsite-util)

## Quickstart

### Install

```bash
$ pip install formsite-util
```

### CLI

TOKEN: Formsite API access token, acquired from account settings

Look at the formsite URL when accessing one of your forms

https:/<span></span>/`SERVER`.formsite.com/`DIRECTORY`/`FORM_ID`

Export a form:

```bash
$ getform -t TOKEN -s SERVER -d DIRECTORY -f FORM_ID -o ./my_export.csv
```

Download files uploaded to a form:

```bash
$ getform -t TOKEN -s SERVER -d DIRECTORY -f FORM_ID -D ./download_dir/
```

### Module

```python
from formsite_util import FormsiteForm, FormsiteFormsList


# Formsite Form
form = FormsiteForm(FORM_ID, TOKEN, SERVER, DIRECTORY)
form.fetch()

df = form.data # data with columns as column IDs
df = form.data_labels # data with columns as the actual labels

# work with df
...

# Formsite Forms List
formlist = FormsiteFormsList(TOKEN, SERVER, DIRECTORY)
formlist.fetch()

forms = formlist.data
# work with forms
...
```

## Overview

This program performs an export of a specified formsite form with parameters
A faster alternative to a manual export from the formsite website. It uses the formsite API v2 to perform exports of results. You can specify parametrs in commandline to filter these results. Allow advanced features like link extraction and even download of files to a specified directory.

Supported python versions: | `3.8` | `3.9` | `3.10+` |

### Dependencies

```txt
aiohttp
requests
tqdm
pytz
pandas
pyarrow # parquet and feather support
openpyxl # excel support
tables # hdf support
```

## Usage

You can invoke the module with `getform [args]` (if it's in your [PATH](https://datatofish.com/add-python-to-windows-path/))

or `py -m formsite_util.cli`

or `python3 -m formsite_util.cli`

You can access the help page with `getform -h`

## **CLI Documentation:**

### **Authorization arguments:**

Authorization arguments are required for all operations.

```bash
getform -t 'TOKEN' -s 'SERVER' -d 'DIRECTORY'
```

**Token**: Your Formsite API token.

**Server**: Your Formsite server. A part of the url. https:/<span></span>/`fsX`.forms… <- the 'fsX' part. For example 'fs4'.

**Directory**: Can be found under [Share > Links > Directory] It is the highlighted part of the url: https:/<span></span>/fsXX.formsite.com/`directory`/hfjfdyjyf

### **Results parameters:**

Results parameters are used to set filters upon the results you are retreiving from a specific form.

**Form**: Can be found under [Share > Links > Directory] It is the highlighted part of the url: https:/<span></span>/fsXX.formsite.com/gnosdH/`form_id` or by running `getform -l` to list all forms and their IDs

#### **Filter by Reference #**

You can provide arguments `--afterref *int* and --beforeref *int*` to specify an interval of which reference numbers to get from your export. It is the same as setting a filter based on reference number when doing an export from the formsite website.

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
--afterref 14856178 --beforeref 15063325 \
-o
```

This will output results in between reference numbers `14856178` and `15063325`.

#### **Filter by Date**

You can provide arguments `--afterdate *date* and --beforedate *date*` to specify an interval of which dates to get from your export. It is the same as setting a filter based on date number when doing an export from the formsite website.

Valid datetime formats are `ISO 8601`, `yyyy-mm-dd` or `yyyy-mm-dd HH:MM:SS`

```txt
ISO 8601 example
yyyy-mm-ddTHH:MM:SSZ
2021-01-20T12:00:00Z is 20th January, 2021 at noon in UTC timezone
```

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
--afterdate '2021-01-01T00:00:00Z' ---beforedate '2021-02-01T00:00:00Z' \
-o
```

This will retrieve all results in for the month of January 2021 in UTC.

#### **Timezone:**

The dates provided are in UTC. This can become a problem if your organizations formsite account is set to a particular timezone you are not in, especially when deleting results/attachments using date filters.

You can set a manual offset with the `-T` or `--timezone` arguments.
Valid input is a timezone database name such as `America/Chicago`. This will shift formsite statistics dates *(columns Date | Start time | Finish time)* and your before/after date argument to your input timezone to the same UTC time but in the target timezone.

Example usage: I want to get results for a certain day in non-UTC timezone. Passing `-T 'America/Chicago'`, my input args `--afterdate 2021-04-10 --beforedate 2021-4-11` will become `2021-04-09 18:00:00` and `2021-04-10 18:00:00`. Additionally, columns Date, Start time, Finish time will also be shifted.

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id' --afterdate '2021-02-01T00:00:00Z' --beforedate '2021-02-01T06:30:00Z' -T 'America/New_York' -o
```

#### **Sorting:**

Invoked with `--sort` [asc|desc] ex: `--sort desc`

Sorts rows based on Reference # column. Defaults to descending.

#### **Results labels and views:**

Results labels are the names of columns of items you put on your form. The default option is to use the default question labels you would put on your form, such as "What is your email address?" or "Your email:" or simply "E-mail:" but for actually working with the data, it is easier and clearer to use a feature formsite supports called Results labels, where you can set your own names of these columns for exports.

You can find the ID of your labels under `[Form Settings > Integrations > Formsite API]`

You can set them with the `--resultslabels *id*` argument. Defaults to 10 which are typically the first results label you add.

You can also set results view with `--resultsview *id*` argument. Defaults to 11 which is all items + statistics.

### **Outputing to a file:**

You can use the `-o` flag to output your export to a file. If you don't specify this flag, no results will be outputted. For reasons as to why you wouldn't include this flag, please see ***File downloads:*** below.

You can leave the `-o` flag by itself or you can specify a path, either relative or absolute to a file you want to output to. If you don't include a path, it will default to its current directory, the file will be a csv with the name in the following format:

```txt
export_formID_date.csv | example: export_formID_2021-04-08--20-00-18.csv
```

The output file changes completely based on what extension you give it. Supported filetypes are:

 | `.csv`
 | `.xlsx`
 | `.parquet`
 | `.feather`
 | `.pkl | .pickle`
 | `.hdf`

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
-o './exports/export_filename.csv'
```

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
-o './output.xlsx'
```

#### **CSV Encoding:**

Specify encoding of the output file (if output format supports it). Defaults to 'utf-8-sig'.

Invoked with `--encoding utf-8`

#### **CSV Delimiter/Separator:**

Specify separator of the output file (if output format supports it). Defaults to ',' (comma)

Invoked with `--separator ','`

#### **CSV Line ending:**

Specify line terminator of the output file (if output format supports it).

Can be one of: { LF, CR, CRLF, os_default }

Invoked with: `--line_terminator os_default`

#### **CSV Quoting:**

Specify quoting level of the output file (if output format supports it). Defaults to 'MINIMAL'

More info about the quoting levels: <https://docs.python.org/3/library/csv.html>

Can be one of: { QUOTE_ALL, QUOTE_MINIMAL, QUOTE_NONNUMERIC, QUOTE_NONE }

Invoked with: `--quoting QUOTE_MINIMAL`

#### **Date format:**

Invoked with `--date_format format` where format is a string of python datetime directives.

Defaults to `'%Y-%m-%d %H:%M:%S'` which is `yyyy-mm-dd HH:MM:SS`

You can find the possible format directives here: <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior>

Sets the date format of all formsite statistics dates such as the Date column. Only applies to CSV output files as excel handles it by itself.

### **File downloads:**

You can use the `-x` flag to extract all links that begin with the formsite base url into a text file, such as:

```txt
https://fsXX.formsite.com/directory/files/f-XXX-XXX-reference#_filename.ext
```

The links file defaults to the same directory as the `getform.py` with the file name `links_{formID}_{timestamp}.txt`

You can use the `-D` option to download all links to a directory you specify, just like with the `-o` argument. The file will be saved with the filename in the link `reference#_filename.ext`

Invoked with: `-D` or `--download` 'path/to/folder' | `-x` or `--extract` path/to/file

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
-D './download_03/' -xre '\.jpg$'
```

*^Example (will create a directory download_03 in the folder where you run it and save all files that end with .jpg uploaded to the form)*

#### **Links regex:**

You can also specify a regex to filter links. You will only get links that contain a match of a regex you provide with the `-xre` or `--extract_regex` option:

```txt
ex: \.json$   - will only return files that end with .json
```

#### **Max concurrent downloads:**

You can specify how many concurrent downloads can take place at any given moment.

Invoked with: `-c x` or `--concurrent_downloads x`

Defaults to `10`

#### **Stop file overwrite:**

If you include this flag, files with the same filenames as you are downloading in the target folder will not be overwritten and re-downloaded.

Invoked with: `-n` or `--dont_overwrite_downloads`

#### **Timeout:**

Timeout in seconds for each individual file download.

If download time exceeds it, it will throw a timeout error and retry up until retries.

Invoked with: `--timeout x`

Defaults to `160` seconds

#### **Retries:**

Number of times to retry downloading files if the download fails.

Invoked with: `--retries x`

Defaults to `3`

#### **Strip prefix:**

If you enable this option, filenames of downloaded files will not have f-xxx-xxx- prefix.

Invoked with: `--strip_prefix`

#### **Filename regex:**

If you include this argument, filenames of the files you download from formsite servers will remove characters that dont match the regex from their filename.

Invoked with: `-Dre` or `--download_regex`

Example: `-Dre '[^\w\_\-]+'` will only keep alphanumeric chars, underscores and dashes in filename.

*^(in case of filename colissions, appends _number)*

### **Other arguments:**

#### **Special options:**

`-h --help` - shows a help message and exits

`--disable_progressbars` or `-P` If you use this flag, program will not display progressbars to console

`-l --list_forms` - prints all forms, can be saved as csv if you provide a path to a file (`-l list.csv`).

*^You can pair this with `getform (...) -l | grep form name` to find form ID easily.*

*Or pipe it into less `getform (...) -l | less` to browse it*


`-V --version` - displays the current version and exits

`-v --verbose` - displays logger *(level DEBUG)* information to stdout, disables progress bars

## **Module Examples:**

### formsite_util

The formsite-util package provides several interfaces for common tasks.

### High level interfaces

FormsiteForm: Represents the form data and session

FormsiteFormsList: Represents the list of all forms for the specified account

FormsiteParameters: Represents parameters for results/items requests

### Low level interfaces

FormFetcher: Result/Item fetching operations *(useful)*

FormParser: Result/Item parsing operations *(useful)*

FormData: Represents the base form data class *(not very useful)*

FormsiteLogger: Custom logger you may connect to your own logging *(not very useful)*

## Module example usage

### FormsiteForm example usage

```python
from formsite_util import FormsiteForm, FormsiteParameters

token = "efwfjwi0fj0W4JG340G343G" # not real token
server = "fs1"
directory = "aqWfcw"

# Get all data for the month of January 2022
params = FormsiteParameters(
    after_date="2022-01-01T00:00:00Z", 
    before_date="2021-02-01T00:00:00Z",
    )

form = FormsiteForm(form_id, token, server, directory)
form.fetch(params=params)
form.data_labels.to_csv('./2022_jan.csv')
```

### FormsiteFormsList example usage
```python
from formsite_util import FormsiteFormsList, FormsiteForm

# Iterate through all forms for the account and fetch them
flist = FormsiteFormsList(token, server, directory)
flist.fetch()

for form_id in flist.data['form_id'].to_list():
    form = FormsiteForm(form_id, token, server, directory)
    form.fetch()
    form.to_csv(f'./expors/{form_id}_data.csv')
```

### Caching example

When fetching a form, it is wasteful to fetch everything again.

We wish to spare the API calls due to the rate limit.

For this reason, you may use caching of the items and results.

```python
from formsite_util import FormsiteForm

form = FormsiteForm(form_id, token, server, directory)


# By adding these parameters to the fetch request...
form.fetch(
    cache_items_path=f'./cache_dir/{form_id}_items.json',
    cache_results_path=f'./cache_dir/{form_id}_data.parquet',
)

# For Items:
#   - You are only re-fetching them if the results labels column IDs don't match the results column IDs (ie. only when necessary)


# For Results:
#   - You are only fetching results since the latest 'id' (aka Reference #) and merging them back
```

### Connecting logging

```python
import logging

# Create your desired handler object
# Example Stream handler
handler = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter("%(message)s")
handler.setLevel(logging.DEBUG)
handler.setFormatter(fmt)

# Add it to the form.logger object using the addHandler method
form.logger.addHandler(handler)

# NOTE: You only need to do this once for all form objects.
#       FormsiteLogger is a singleton, only 1 instance may exist at any time.
#       To do this once at the start of your program, you can do this:

from formsite_util.logger import FormsiteLogger
l = FormsiteLogger()
l.addHandler(...)

```

### FormsiteForm class

```python
from formsite_util import FormsiteForm, FormsiteParameters

form = FormsiteForm(...)
params = FormsiteParameters(...)

form.fetch(fetch_results=True, # Populates form.data
           fetch_items=True,   # Populates form.items, form.labels
           fetch_delay=3.0,    # delay between each API call in seconds
           params=params,      # Results parameters
           result_labels_id=0, # Items labels ID found in [Form settings -> Integrations -> Formsite API]
           )

df1 = form.data 
# DataFrame with columns as column IDs used by formsite
# returns data if results were fetched

df2 = form.data_labels 
# DataFrame with columns as labels of (result_labels_id)
# data_labels only returns data, if both results and items were fetched

labels_dict = form.labels 
# The mapping of column ID -> label
# returns data if items were fetched

items_dict = form.items 
# The original, unparsed formsite items object
# returns data if items were fetched


form.extract_urls(...)
# Extracts URLs to all files uploaded to the form using bult in controls

form.downloader(...)
# Launches a syncrhonous downloader of the files uploaded to the form

form.async_downloader(...)
# Launches an async downloader of the files uplaoded to the form

form.to_csv(...)
# Saves the form data or data_labels to a CSV file with the following default settings:
#   - by default save data_labels
#   - encoded as utf-8-sig (utf-8 with BOM)
#   - index=False
#   - %Y-%m-%d %H:%M:%S datetime format

form.to_excel(...)
# Saves the form data or data_labels to an Excel file with the following default settings:
#   - by default save with data_labels
#   - index=False

```

### FormsiteFormsList class

```python
from formsite_util import FormsiteFormsList

flist = FormsiteFormsList(...)

flist.fetch()

flist.data
# DataFrame in the format:
# form_id | name | state | results_count | files_size | files_size_human | url
# ...
```

## Notes

More info can be found at Formsite API v2 help page

**<https://support.formsite.com/hc/en-us/articles/360000288594-API>**

You can find API related information of your specific form under:

```txt
[Form Settings > Integrations > Formsite API] on the Formstie website
```

**API response error codes table:**

| code | description                                 |
|------|---------------------------------------------|
| 401  | Authentication info is missing or invalid.  |
| 403  | Forbidden.                                  |
| 404  | Path or object not found.                   |
| 422  | Invalid parameter.                          |
| 429  | Too many requests or too busy.              |
| 5xx  | Unexpected internal error.                  |

## License

© 2022 Jakub Strnad

MIT License
Please see LICENSE.<span></span>md for more details.
