# Formsite Utility

## A CLI API-based tool.

## Overview

This program performs an export of a specified formsite form with parameters. 
A faster alternative to a manual export from the formsite website. It uses the formsite API v2 to perform exports of results. You can specify parametrs in commandline to filter these results. Allow afvanced features like link extraction and even download of files to a specified directory.

## Installation

You can install the required packages with:
`pip install -r requirements.txt`

## Usage

**Required arguments:**
```
python getform.py -u USERNAME -t TOKEN -f FORM -s SERVER -d DIRECTORY
```
**Optional arguments:**
```
[-h] [--afterref AFTERREF] [--beforeref BEFOREREF] [--afterdate AFTERDATE] [--beforedate BEFOREDATE] [--resultslabels RESULTSLABELS] [-r] [-o [OUTPUT_FILE]] [-x [EXTRACT_LINKS]] [-X LINKS_REGEX] [-D [DOWNLOAD_LINKS]] [--sort {asc,desc}] [-l] [-g] [-V] [-H] [--no_items]
```



```
Arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Username of the account used to create your API token. Required.
  -t TOKEN, --token TOKEN
                        Your Formsite API token. Required.
  -f FORM, --form FORM  Your Formsite form ID. Can be found under [Share > Links > Directory]. Required.
  -s SERVER, --server SERVER
                        Your Formsite server. A part of the url. https://fsX.forms... <- the fsX part. Required.
  -d DIRECTORY, --directory DIRECTORY
                        Your Formsite directory. Can be found under [Share > Links > Directory]. Required.
  --afterref AFTERREF   Get results greater than a specified Reference #. Must be an integer.
  --beforeref BEFOREREF
                        Get results lesser than a specified Reference #. Must be an integer.
  --afterdate AFTERDATE
                        Get results after a specified date. Must be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS. This date is in your local timezone (unless UTC formatted).
  --beforedate BEFOREDATE
                        Get results before a specified date. Must be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS. This date is in your local timezone (unless UTC formatted).
  --resultslabels RESULTSLABELS
                        Use specific results labels for your CSV headers. Defaults to 0, which takes the first set results labels or if those are not available, default question labels.
  -r, --refresh_headers
                        If you include this flag, items_formid.json will be re-downloaded with latest headers.
  -o [OUTPUT_FILE], --output_file [OUTPUT_FILE]
                        Specify output file name and location. Defaults to export_yyyymmdd_formid.csv in the folder of the script.
  -x [EXTRACT_LINKS], --extract_links [EXTRACT_LINKS]
                        If you include this flag, you will get a text file that has all links that start with formsite url stored. You can specify file name or location, for example '-x
                        C:\Users\MyUsername\Desktop\download_links.txt'. If you don't specify a location, it will default to the folder of the script.
  -X LINKS_REGEX, --links_regex LINKS_REGEX
                        Keep only links that match the regex you provide. Won't do anything if -x or -d arguments are not provided. Defaults to '.+'. Example usage: '-X \.json$' would only give you files that have .json  
                        extension.
  -D [DOWNLOAD_LINKS], --download_links [DOWNLOAD_LINKS]
                        If you include this flag, all formsite links in the export will be downloaded to a folder. You can specify location, for example '-d C:\Users\MyUsername\Desktop\downloads'. If you don't specify a  
                        location, it will default to the folder of the script.
  --sort {asc,desc}     Determines how the output CSV will be sorted. Defaults to descending.
  -l, --list_columns    If you use this flag, program will output mapping of what column belongs to which column ID instead of actually running, useful for figuring out search arguments.
  -g, --generate_results_files
                        If you use this flag, program will output raw results in json format from API requests. Useful for debugging purposes.
  -V, --version         Returns version of the script.
  -H, --headers         Prints the headers from the first results API request, then quits the program. Overrides other options.
  --no_items            If you use this flag, program will not store headers for later use.
```


## Notes

More info can be found at Formsite API v2 help page: https://support.formsite.com/hc/en-us/articles/360000288594-API You can find API related information of your specific form under: 

**[Form Settings > Integrations > Formsite API]**