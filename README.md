# Formsite Utility

CLI tool + module for formsite automation.

## Overview

This program performs an export of a specified formsite form with parameters
A faster alternative to a manual export from the formsite website. It uses the formsite API v2 to perform exports of results. You can specify parametrs in commandline to filter these results. Allow advanced features like link extraction and even download of files to a specified directory.

### Installation

You can install the module with

`pip install formsite-util`

or download it manually from releases.

The required packages are:

```txt
aiofiles
aiohttp
datetime
openpyxl
pandas
python_dateutil
pytz
regex
requests
tqdm
```

### Usage

You can invoke the module with `getform [args]`

You can access the help page with **`getform -h`**

**Required arguments:**

```bash
getform -u 'USERNAME' -t 'TOKEN' -s 'SERVER' -d 'DIRECTORY' -f '[FORM]'
```

**Optional arguments:**

```txt
[-h] [--afterref AFTERREF] [--beforeref BEFOREREF] [--afterdate AFTERDATE] [--beforedate BEFOREDATE] [--resultslabels RESULTSLABELS] [-r] [-o [OUTPUT_FILE]] [-x [EXTRACT_LINKS]] [-X LINKS_REGEX] [-D [DOWNLOAD_LINKS]] [--sort {asc,desc}] [-l] [-g] [-V] [-H] [--no_items]
```

## **CLI Examples:**

**`NOTE:` QUOTES AROUND ARGUMENTS ARE OPTIONAL**

### **Login arguments:**

Login arguments are required for nearly all operations.


```bash
getform -u 'USERNAME' -t 'TOKEN' -s 'SERVER' -d 'DIRECTORY'
```

**Username**: Username of the account used to create your API token

**Token**: Your Formsite API token.

**Server**: Your Formsite server. A part of the url. https:/<span></span>/`fsX`.forms… <- the 'fsX' part. For example 'fs22'.

**Directory**: Can be found under [Share > Links > Directory] It is the highlighted part of the url: https:/<span></span>/fsXX.formsite.com/`gnosdH`/hfjfdyjyf

### **Results parameters:**

Results parameters are used to set filters upon the results you are retreiving from a specific form. All but the `--form` argument are optional.

**Form**: Can be found under [Share > Links > Directory] It is the highlighted part of the url: https:/<span></span>/fsXX.formsite.com/gnosdH/`hfjfdyjyf` or by running `getform -L` to list all forms and their IDs

#### **After and before Reference #**

You can provide arguments `--afterref *int* and --beforeref *int*` to specify an interval of which reference numbers to get from your export. It is the same as setting a filter based on reference number when doing an export from the formsite website.

```bash
getform -u 'username' -t 'token' -f 'form_id' -d 'directory' -s 'server'  --afterref 14856178 ---beforeref 15063325 -o
```

This will retrieve all results in between reference numbers `14856178` and `15063325`. You can also specify only afterref or only beforeref by itself, which would give you its respective results. You can also omit this argument entierly, which would give you all results currently present in the form.

#### **After and before Date**

You can provide arguments `--afterdate *date* and --beforedate *date*` to specify an interval of which dates to get from your export. It is the same as setting a filter based on date number when doing an export from the formsite website.

Valid input formats for date are `ISO 8601`, `yyyy-mm-dd` or `yyyy-mm-dd HH:MM:SS`

```txt
ISO 8601 example
yyyy-mm-ddTHH:MM:SSZ  
2021-01-20T12:00:00Z is 20th Januray, 2021 at noon
```

```bash
getform -u username -t token -f form_id -d directory -s server --afterdate '2021-01-01T00:00:00Z' ---beforedate '2021-02-01T00:00:00Z' -o
```

This will retrieve all results in for the month of January. You can also specify only afterdate or only beforedate by itself, which would give you its respective results. You can also omit this argument entierly, which would give you all results currently present in the form.

#### **Timezone:**

The dates provided are in your **local timezone**. This can become a problem if your organizations' formsite account is set to a particular timezone you are not in, especially when deleting results/attachments using date filters. 

You can set a manual offset with the `-T` or `--timezone` arguments.
They take either an offset in the `+05:00` | `-03:00` format or a timezone databse name such as `US/Central`. This will shift formsite statistics dates *(column Date for example)* and your input before/after date argument to your input timezone.

```bash
getform -u 'username' -t 'token' -f 'form_id' -d 'directory' -s 'server' --afterdate '2021-02-01T00:00:00Z' ---beforedate '2021-02-01T06:30:00Z' -o -T 'America/New_York'
```

#### **Date format:**

Invoked with `-F format` or `--date_format format` where format is a string of python datetime directives.

Defaults to `'%Y-%m-%d %H:%M:%S'` which is `yyyy-mm-dd HH:MM:SS`

You can find the possible format directives here: <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior>

Sets the date format of all formsite statistics dates such as the Date column. Only applies to CSV output files as excel handles it by itself.

#### **Sorting:**

Invoked with `--sort` [asc|desc] ex: `--sort asc`

Sorts rows based on Reference # column.

#### **Results labels and views:**

Results labels are the names of columns of items you put on your form. The default option is to use the default question labels you would put on your form, such as "What is your email address?" or "Your email:" or simply "E-mail:" but for actually working with the data, it is easier and clearer to use a feature formsite supports called Results labels, where you can set your own names of these columns for exports.

You can find the ID of your labels under `[Form Settings > Integrations > Formsite API]`

You can set them with the `--resultslabels *id*` argument. Defaults to 10 which are typically the first results label you add.

You can also set results view with `--resultsview *id*` argument. Defaults to 11 which is all items + statistics.

### **Functional arguments:**

#### **Outputing to a file:**

You can use the `-o` flag to output your export to a file. If you don't specify this flag, no results will be outputted. For reasons as to why you wouldn't include this flag, please see ***File downloads:*** below.

You can leave the `-o` flag by itself or you can specify a path, either relative or absolute to a file you want to output to. If you don't include a path, it will default to its current directory, the file will be a csv with the name in the following format:

```txt
export_formID_date.csv
```

If you specify the file extension to be `.xlsx` the results export will be an excel file. If you don't or you choose a format other than excel, you will get a `.csv`

```bash
getform -u 'username' -t 'token' -f 'form_id' -d 'directory' -s 'server' -o ./exports/export_projectName.csv
```

**`NOTE:` Putting the path in quotes is optional, but REQUIRED if your path contains a space**

#### **File downloads:**

You can use the `-x` flag to extract all links that begin with the formsite base url into a text file, such as:

```txt
https://fsXX.formsite.com/directory/files/f-XXX-XXX-reference#_filename.ext
```

The links file defaults to the same directory as the `getform.py` with the file name `links_{formID}_{timestamp}.txt`

You can use the `-D` option to download all links to a directory you specify, just like with the `-o` argument. The file will be saved with the filename in the link `reference#_filename.ext`

```bash
getform -u 'username' -t 'token' -f 'form_id' -d 'directory' -s 'server' -D './download_03/' -X '\.jpg$'
```

*will create a directory download_03 in the same folder as formsite_utility.py and save all jpg files uploaded to the form*

### **Functional parameters:**

#### **Links regex:**

You can also specify a regex to filter links. You will only get links that contain a match of a regex you provide with the `-X` option:

```txt
ex: \.json$   - will only return files that end with .json
```

#### **Max concurrent downloads:**

You can specify how many concurrent downloads can take place with the `-c x` option where x is the number of maximum concurrent downloads. 

Defaults to `10`.

### **Other arguments:**

#### **Special options:**

These options overwrite the core functionality of the program.

`-h --help` - shows a help message

`-l --list_columns` - shows you the IDs of each column

`-L --list_forms` - prints all forms, can be saved as csv

`-V --version` - displays the current version of the programs and checks for updates

## **Module Examples:**

```python
# Example functionality in your program
from formsite_util import FormsiteInterface, FormsiteCredentials, FormsiteParams

# required information is form id and access credentials
# result parameters are optional
form_id = 'yourFormsID'
login = FormsiteCredentials('yourUsername','yourToken','yourServer','yourDirectory')
my_params = FormsiteParams(afterdate='2021-04-01', timezone='America/Chicago')

# you dont have to use a context manager
# you can also use `interface = FormsiteInterface(...)`
with FormsiteInterface(form_id, login, params=my_params) as interface:

    # list all forms on account and save them to a csv
    interface.ListAllForms(save2csv='./my_list_of_all_forms.csv')

    # export form to a file
    interface.WriteResults('./my_results.csv')

    # download all files submitted to your form
    interface.DownloadFiles('./dl_folder/', max_concurrent_downloads = 100, overwrite_existing=False)

    # dowloaded files' filenames will only have characters that match the regex
    interface.DownloadFIles('./dl_folder2/', filename_regex=r'[^A-Za-z0-9\_\-]+')

    # extract all links to files that match a regex
    json_files_in_form = interface.ReturnLinks(links_regex=r'\.json$')

    # export results to pandas dataframe
    my_form_as_dataframe = interface.ReturnResults()
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
Please see LICENSE.md for more details.
