# Formsite Utility

## A CLI API-based tool.

## Overview

This program performs an export of a specified formsite form with parameters. 
A faster alternative to a manual export from the formsite website. It uses the formsite API v2 to perform exports of results. You can specify parametrs in commandline to filter these results. Allow afvanced features like link extraction and even download of files to a specified directory.

## Installation

You can install the required packages with:
`pip install -r requirements.txt`

The required packages are:
```
regex
openpyxl
aiohttp
requests
pandas
pytz
python_dateutil
```

## Usage

**Required arguments:**
```
python getform.py -u USERNAME -t TOKEN -f FORM -s SERVER -d DIRECTORY
```
**Optional arguments:**
```
[-h] [--afterref AFTERREF] [--beforeref BEFOREREF] [--afterdate AFTERDATE] [--beforedate BEFOREDATE] [--resultslabels RESULTSLABELS] [-r] [-o [OUTPUT_FILE]] [-x [EXTRACT_LINKS]] [-X LINKS_REGEX] [-D [DOWNLOAD_LINKS]] [--sort {asc,desc}] [-l] [-g] [-V] [-H] [--no_items]
```

# **Examples:**
## **Outputing to a file:**

You can use the `-o` flag to output your export to a file. If you don't specify this flag, no results will be outputted. For reasons as to why you wouldn't include this flag, please see ***File downloads:*** below.

You can leave the `-o` flag by itself or you can specify a path, either relative or absolute to a file you want to output to. If you don't include a path, it will default to its current directory, the file will be a csv with the name in the following format:
```
export_formID_date.csv
```
If you specify the file extension to be `.xlsx` the results export will be an excel file. If you don't or you choose a format other than excel, you will get a `.csv`

On Windows in either powershell or cmd:
```powershell
> python .\getform.py -u username -t token -f form_id -d directory -s server -o .\exports\export_projectName.xlsx
```

On Unix:
```bash
$ python3 getform.py -u username -t token -f form_id -d directory -s server -o ./exports/export_projectName.csv
```
**NOTE: `PUTTING THE PATH IN QUOTES IS OPTIONAL, but recommended if your path contains a space`**

## **After and before Reference #**:

You can provide arguments `--afterref *int* and --beforeref *int*` to specify an interval of which reference numbers to get from your export. It is the same as setting a filter based on reference number when doing an export from the formsite website.

On Windows in powershell or cmd, run:
```
> python .\getform.py -u username -t token -f form_id -d directory -s server --afterref 14856178 ---beforeref 15063325 -o
```
On Unix:
```bash
$ python3 getform.py -u username -t token -f form_id -d directory -s server --afterref 14856178 ---beforeref 15063325 -o
```
This will retrieve all results in between reference numbers 14856178 and 15063325. You can also specify only afterref or only beforeref by itself, which would give you its respective results. You can also omit this argument entierly, which would give you all results currently present in the form.

## **After and before Date**:

You can provide arguments `--afterdate *date* and --beforedate *date*` to specify an interval of which dates to get from your export. It is the same as setting a filter based on date number when doing an export from the formsite website. 

The date must be in `ISO 8601` format, which in other words means:
```
yyyy-mm-ddTHH:MM:SSZ  example: 2021-01-20T12:00:00Z is 20th Januray, 2021 at noon
```

On Windows in powershell or cmd:
```powershell
> python .\getform.py -u username -t token -f form_id -d directory -s server --afterdate '2021-01-01T00:00:00Z' ---beforedate '2021-02-01T00:00:00Z' -o
```
On Unix:
```bash
$ python3 getform.py -u username -t token -f form_id -d directory -s server --afterdate '2021-01-01T00:00:00Z' ---beforedate '2021-02-01T00:00:00Z' -o
```
**NOTE: `THE QUOTES ARE OPTIONAL`**

This will retrieve all results in for the month of January. You can also specify only afterdate or only beforedate by itself, which would give you its respective results. You can also omit this argument entierly, which would give you all results currently present in the form.

### Warning:

The dates provided are in your **local timezone**. This can become a problem if your organizations' formsite account is set to a particular timezone you are not in, especially when deleting results/attachments using date filters. *Please be careful and account for the offset.*

## **File downloads:**

You can use the `-x` flag to extract all links that begin with the formsite base url into a text file, such as:
```
https://fsXX.formsite.com/directory/files/f-XXX-XXX-reference#_filename.ext
```
The links file defaults to the same directory as the `getform.py` with the file name `links_{formID}_{timestamp}.txt`

You can use the `-D` option to download all links to a directory you specify, just like with the `-o` argument. The file will be saved with the filename in the link `reference#_filename.ext`

### Links regex:

You can also specify a regex to filter links. You will only get links that contain a match of a regex you provide with the `-X` option:
```
ex: \.json$   - will only return files that end with .json
```

On Windows in either powershell or cmd:
```powershell
> python .\getform.py -u username -t token -f form_id -d directory -s server -x -X \.png$
```
*will return a links.txt with links to all png files in export*

On Unix:
```bash
$ python3 ./getform.py -u username -t token -f form_id -d directory -s server -D './download_03/' -X \.jpg$
```
*will create a directory download_03 in the same folder as getform.py and save all jpg files in the export there*

## **Results labels:**

Results labels are the names of columns of items you put on your form. The default option is to use the default question labels you would put on your form, such as "What is your email address?" or "Your email:" or simply "E-mail:" but for actually working with the data, it is easier and clearer to use a feature formsite supports called Results labels, where you can set your own names of these columns for exports. 

You can find the ID of your labels under `[Form Settings > Integrations > Formsite API]`

You can set them with the `--resultslabels *id*` argument.

## **Other options:**

Among other toggleable options are:

`-h --help` - shows a help message

`-r --refresh_headers` - re-downloads items.json, a file that contains header labels of your particular results labels.

`--sort [asc | desc]` - an option that sorts reference numbers in ascending or descending order, defaults to descending

`-l --list_columns` - shows you the IDs of each column, useful for the 
`--search_xxx` options (*NOT YET IMPLEMENTED*)

`-g --generate_results` - by default, the results.json file you get from the API requests are not saved. if you include this option, you will save them

`-V --version` - displays the current version of the programs and checks for updates

`-v --verbose` - displays more information about the progress of the program

`--no_items` - by default, items.json is saved in the same directory as getform.py, this can save 1 API call because it won't have to request it again unless you specify otherwise with `-r`. if you include this option, items.json will not be saved

# Notes

More info can be found at Formsite API v2 help page: 

**https://support.formsite.com/hc/en-us/articles/360000288594-API**

You can find API related information of your specific form under:
```
[Form Settings > Integrations > Formsite API] on the Formstie website
```
**API response error codes table:**
```
| code | description                                 |
| 401  | Authentication info is missing or invalid.  |
| 403  | Forbidden.                                  |
| 404  | Path or object not found.                   |
| 422  | Invalid parameter.                          |
| 429  | Too many requests or too busy.              |
| 5xx  | Unexpected internal error.                  |
```