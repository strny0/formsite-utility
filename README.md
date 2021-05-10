# Formsite Utility

CLI tool + module for formsite automation.

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/31145f1b97934080981a53783803701f)](https://www.codacy.com/gh/strny0/formsite-utility/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=strny0/formsite-utility&amp;utm_campaign=Badge_Grade)
[![PyPI version](https://badge.fury.io/py/formsite-util.svg)](https://badge.fury.io/py/formsite-util)
![PyPI - Downloads](https://img.shields.io/pypi/dm/formsite-util)

## Overview

This program performs an export of a specified formsite form with parameters
A faster alternative to a manual export from the formsite website. It uses the formsite API v2 to perform exports of results. You can specify parametrs in commandline to filter these results. Allow advanced features like link extraction and even download of files to a specified directory.

Supported python versions: | `3.6` | `3.7` | `3.8` | `3.9+` |

## Installation

Unix (macOS, linux):

```bash
pip3 install formsite-util
```

Windows:

```cmd
pip install formsite-util
```

The required packages are:

```txt
pytz>=2021.1
pandas>=1.2.4
tqdm>=4.60.0
regex>=2021.4.4
aiohttp>=3.7.4.post0
requests>=2.25.1
aiofiles>=0.6.0
dataclasses>=0.8
python_dateutil>=2.8.1
```

Recommended packages:

```txt
colorama (for fixing broken console progressbars)
pyarrow or fastparquet (engine for writing to parquet)
openpyxl (engine for writing to excel)
```

## Usage

You can invoke the module with `getform [args]` (if it's in your [PATH](https://datatofish.com/add-python-to-windows-path/))

or `py -m formsite_util.cli`

or `python3 -m formsite_util.cli`

You can access the help page with **`getform -h`**

## **CLI Documentation:**

**`NOTE:` QUOTES AROUND ARGUMENTS ARE OPTIONAL**

### **Authorization arguments:**

Authorization arguments are required for nearly all operations.

```bash
getform -t 'TOKEN' -s 'SERVER' -d 'DIRECTORY'
```

**Token**: Your Formsite API token.

**Server**: Your Formsite server. A part of the url. https:/<span></span>/`fsX`.forms… <- the 'fsX' part. For example 'fs22'.

**Directory**: Can be found under [Share > Links > Directory] It is the highlighted part of the url: https:/<span></span>/fsXX.formsite.com/`gnosdH`/hfjfdyjyf

### **Results parameters:**

Results parameters are used to set filters upon the results you are retreiving from a specific form. All but the `--form` argument are optional.

**Form**: Can be found under [Share > Links > Directory] It is the highlighted part of the url: https:/<span></span>/fsXX.formsite.com/gnosdH/`hfjfdyjyf` or by running `getform -L` to list all forms and their IDs

#### **After and before Reference #**

You can provide arguments `--afterref *int* and --beforeref *int*` to specify an interval of which reference numbers to get from your export. It is the same as setting a filter based on reference number when doing an export from the formsite website.

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
--afterref 14856178 --beforeref 15063325 \
-o
```

This will output a csv with results in between reference numbers `14856178` and `15063325`.

#### **After and before Date**

You can provide arguments `--afterdate *date* and --beforedate *date*` to specify an interval of which dates to get from your export. It is the same as setting a filter based on date number when doing an export from the formsite website.

Valid datetime formats are `ISO 8601`, `yyyy-mm-dd` or `yyyy-mm-dd HH:MM:SS`

```txt
ISO 8601 example
yyyy-mm-ddTHH:MM:SSZ  
2021-01-20T12:00:00Z is 20th Januray, 2021 at noon
```

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
--afterdate '2021-01-01T00:00:00Z' ---beforedate '2021-02-01T00:00:00Z' \
-o
```

This will retrieve all results in for the month of January.

#### **Timezone:**

The dates provided are in your **local timezone**. This can become a problem if your organizations' formsite account is set to a particular timezone you are not in, especially when deleting results/attachments using date filters.

You can set a manual offset with the `-T` or `--timezone` arguments.
Valid input can be an offset in the `+05:00` | `-03:00` or `+0500` format or a timezone databse name such as `America/Chicago`. This will shift formsite statistics dates *(column Date Start/End time for example)* and your before/after date argument to your input timezone by a timedelta of your `local time - target time`.

Example offset: I am in `CET`, passing `-T 'America/Chicago'`. My input afterdate is `--afterdate 2021-04-10`. It will become `2021-04-09 17:00:00` as the timezone difference between these 2 zones is 7 hours (in daylight savings time). Additionally, columns Date, Start time, End Time will also be shifted by 7 hours back.

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
--afterdate '2021-02-01T00:00:00Z' ---beforedate '2021-02-01T06:30:00Z' \
-T 'America/New_York' -o
```

#### **Sorting:**

Invoked with `--sort` [asc|desc] ex: `--sort asc`

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
export_formID_date.csv => eg. export_JFa87fa_2021-04-08--20:00:18.csv
```

The output file changes completely based on what extension you give it. Supported filetypes are:

 | `.csv`
 | `.xlsx`
 | `.json`
 | `.pkl`
 | `.pickle`
 | `.parquet`
 | `.md`
 | `.txt`
 |

*(json returns a records oriented array, in case of duplicate column names appends a _number)*

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
-o './exports/export_filename.csv'
```

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
-o './output.json'
```

#### **CSV Encoding:**

Specify encoding of the output file (if output format supports it). Defaults to 'utf-8'

Invoked with `--encoding utf-8`

#### **CSV Delimiter/Separator:**

Specify separator of the output file (if output format supports it). Defaults to ',' (comma)

Invoked with `--separator ,`

#### **CSV Line ending:**

Specify line terminator of the output file (if output format supports it). Defaults to '\n' (LF) (newline)

Can be one of: { LF, CR, CRLF }

Invoked with: `--line_terminator LF`

#### **CSV Quoting:**

Specify quoting level of the output file (if output format supports it). Defaults to 'MINIMAL'

More info about the quoting levels: <https://docs.python.org/3/library/csv.html>

Can be one of: { ALL, MINIMAL, NONNUMERIC, NONE }

Invoked with: `--quoting MINIMAL`

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

Invoked with: `-D` or `--download` 'path/to/folder' | `-x` or `--extract_links` path/to/file

Example:

```bash
$ getform -t 'token' -d 'directory' -s 'server' -f 'form_id'  \
-D './download_03/' -X '\.jpg$'
```

##### (will create a directory download_03 in the folder where you run it and save all files that end with .jpg uploaded to the form)

#### **Links regex:**

You can also specify a regex to filter links. You will only get links that contain a match of a regex you provide with the `-X` option:

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

Defaults to `80` seconds

#### **Retries:**

Number of times to retry downloading files if the download fails.

Invoked with: `--retries x`

Defaults to `1`

#### **Strip prefix:**

If you enable this option, filenames of downloaded files will not have f-xxx-xxx- prefix.

Invoked with: `--stripprefix`

#### **Filename regex:**

If you include this argument, filenames of the files you download from formsite servers `will remove characters that dont match the regex` from their filename.

Invoked with: `-R` or `--filename_regex`

Example: `-R '[^\w\_\-]+'` will only keep alphanumeric chars, underscores and dashes in filename.

##### (in case of filename colissions, appends _number)

#### **Get download status:**

If you enable this option, a text file with status for each downloaded link will be saved (complete or incomplete). Will contain detailed reason why it failed for each link.

Invoked with: `--get_download_status`

### **Other arguments:**

#### **Special options:**

`-h --help` - shows a help message and exits

`--disable_progressbars` If you use this flag, program will not display progressbars to console

`-l --list_columns` - shows you the IDs of each column and exits

`-L --list_forms` - prints all forms, can be saved as csv if you provide a path to a file (`-L list.csv`).

##### You can pair this with `getform (...) -L | grep form name` to find form ID easily

`-V --version` - displays the current version and exits

## **Module Examples:**

**All methods and classes have docstrings and are typed**

```python
# Example functionality in your program
from formsite_util import FormsiteInterface, FormsiteCredentials, FormsiteParams

# required information is form id and access credentials
# result parameters are optional
form_id = 'yourFormsID'
form_id = 'xAf93cf' # example

login = FormsiteCredentials('yourToken','yourServer','yourDirectory')
login = FormsiteCredentials('kDawe9gar984j093gihn94','fs22','Wa1fn8') # example

my_params = FormsiteParams(afterdate='2021-04-01', timezone='America/Chicago')

# context manager use is optional
# you can also use `interface = FormsiteInterface(...)`
with FormsiteInterface(form_id, login, params=my_params) as interface:

    # list all forms on account and save them to a csv
    interface.ListAllForms(save2csv='./my_list_of_all_forms.csv')

    # export form to a file
    interface.WriteResults('./my_results.csv')

    # download all files submitted to your form
    interface.DownloadFiles('./dl_folder/',
                            max_concurrent_downloads = 100,
                            overwrite_existing = False)

    # dowloaded files' filenames will only have characters that match the regex
    interface.DownloadFIles('./dl_folder2/', filename_regex=r'[^A-Za-z0-9\_\-]+')

    # extract all links to files that match the regex - files that end with .json
    json_files_in_form = interface.ReturnLinks(links_regex=r'\.json$')

    # export results to pandas dataframe
    my_form_as_dataframe = interface.ReturnResults()
    # or 
    my_form_as_dataframe = interface.Data
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

© 2021 Jakub Strnad

This program is licensed under GPLv3
Please see LICENSE.<span></span>md for more details.
