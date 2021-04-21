#!/usr/bin/env python3
# Script: getform.py
# Author: Jakub Strnad
# Description: This script uses the formsite API to do an export. For more info, execute with -h or --help argument
# Notes:    items - headers of the exported CSV
#			results - remaining rows of the exported CSV
#           API headers - information being sent as a part of the API request, eg. authorization, parameters
#           Rate limits - formsite API allows max 2000 calls total per day or max 50 per minute, keep that in mind when using this script
#
# File organization:
#   1. imported modules
#   2. methods
#   3. program execution, usage of methods

import sys #s         #s - standard library, #! - 3rd party module
from datetime import datetime as dt #s
from datetime import timedelta as td #s
import time #s
from io import open as open #s
import os #s
from pathlib import Path as Path #s
import json #s
import csv #s
import argparse #s
import logging #s
import concurrent.futures
import requests

import pytz
import dateutil as du #1
import regex #!
import asyncio #!
import aiohttp #!
import pandas as pd #!
import openpyxl #!

##              ##
##   PROMPTS    ##
##              ##

# Sets parameters/arguments getform.py takes
def __setup_arguments__(): 
    parser = argparse.ArgumentParser(
        description="Github of author: https://github.com/strny0/formsite-utility\n"
                    "This program performs an export of a specified formsite form with parameters.\n"
                    "A faster alternative to a manual export from the formsite website, that can be used for workflow automation.\n"
                    "Allows for the extraction of assets saved on formsite servers.",
        epilog=     "More info can be found at Formsite API v2 help page:    \n"
                    "https://support.formsite.com/hc/en-us/articles/360000288594-API    \n"
                    "You can find API related information of your specific form under: [Form Settings > Integrations > Formsite API] \n"
                    "API response error codes table:\n"
                    "| code | description                                 |\n"
                    "| 401  | Authentication info is missing or invalid.  |\n"
                    "| 403  | Forbidden.                                  |\n"
                    "| 404  | Path or object not found.                   |\n"
                    "| 422  | Invalid parameter.                          |\n"
                    "| 429  | Too many requests or too busy.              |\n"
                    "| 5xx  | Unexpected internal error.                  |\n",
                    formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-u','--username', type=str, default=None,
                        help="Username of the account used to create your API token. Required."
                        )
    parser.add_argument('-t', '--token', type=str, default=None,
                        help="Your Formsite API token. Required."
                        )
    parser.add_argument('-f', '--form', type=str, default=None,
                        help="Your Formsite form ID. Can be found under [Share > Links > Directory]. Required."
                        )
    parser.add_argument('-s', '--server', type=str, default=None,
                        help="Your Formsite server. A part of the url. https://fsX.forms... <- the fsX part. For example 'fs22'. Required."
                        )
    parser.add_argument('-d', '--directory', type=str, default=None,
                        help="Your Formsite directory. Can be found under [Share > Links > Directory]. Required."
                        )
    parser.add_argument('--afterref', type=int, default=0, 
                        help="Get results greater than a specified Reference #. \nMust be an integer."
                        )
    parser.add_argument('--beforeref', type=int, default=0, 
                        help="Get results lesser than a specified Reference #. \nMust be an integer."
                        )
    parser.add_argument('--afterdate', type=str, default="", 
                        help="Get results after a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS. \nThis date is in your local timezone, unless specified otherwise."
                        )
    parser.add_argument('--beforedate', type=str, default="", 
                        help="Get results before a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS. \nThis date is in your local timezone, unless specified otherwise."
                        )
    parser.add_argument('--resultslabels', type=int, default=0, 
                        help="Use specific results labels for your CSV headers. \nDefaults to 0, which takes the first set results labels or if those are not available, default question labels."
                        )
    parser.add_argument('-r', '--refresh_headers', action="store_true",  default=False, 
                        help="If you include this flag, items_formid.json will be re-downloaded with latest headers."
                        )
    parser.add_argument('-o', '--output_file', nargs='?', default=False, const=Path.cwd(), 
                        help="Specify output file name and location. \nDefaults to export_yyyymmdd_formid.csv in the folder of the script."
                        )
    parser.add_argument('-x', '--extract_links', nargs='?',  default=False, const=Path.cwd(), #+f'\\links_{dt.now().strftime("%Y%m%d")}.txt 
                        help="If you include this flag, you will get a text file that has all links that start with formsite url stored. \nYou can specify file name or location, for example '-x C:\\Users\\MyUsername\\Desktop\\download_links.txt'. \nIf you don't specify a location, it will default to the folder of the script."
                        )
    parser.add_argument('-X', '--links_regex', type=str,  default='.+', 
                        help="Keep only links that match the regex you provide. \nWon't do anything if -x or -d arguments are not provided. \nDefaults to '.+'. Example usage: '-X \\.json$' would only give you files that have .json extension."
                        )
    parser.add_argument('-D', '--download_links', nargs='?',  default=False, const=Path.cwd().joinpath(f'./download_{dt.now().strftime("%Y-%m-%d--%H-%M-%S")}'),
                        help="If you include this flag, all formsite links in the export will be downloaded to a folder."
                        "\nYou can specify location, for example `-D 'C:\\Users\\My Username\\Desktop\\downloads'` ."
                        "\nIf you don't specify a location, it will default to the folder of the script."
                        )
    parser.add_argument('--sort', choices=['asc', 'desc'], type=str,  default="desc", 
                        help="Determines how the output CSV will be sorted. Defaults to descending."
                        )
    parser.add_argument('-l', '--list_columns', action="store_true",  default=False, 
                        help="If you use this flag, program will output mapping of what column belongs to which column ID instead of actually running, useful for figuring out search arguments."
                        )
    parser.add_argument('-g', '--generate_results_files', action="store_true",  default=False, 
                        help="If you use this flag, program will output raw results in json format from API requests."
                        "\nUseful for debugging purposes."
                        )
    parser.add_argument('-V', '--version', action="store_true",  default=False, 
                        help="Returns version of the script."
                        )
    parser.add_argument('-H','--headers', action="store_true",  default=False, 
                        help="Prints the headers from the first results API request, then quits the program. Overrides other options."
                        )
    parser.add_argument('--no_items', action="store_false",  default=True, 
                        help="If you use this flag, program will not store headers for later use."
                        )
    parser.add_argument('-v','--verbose', action="store_true",  default=False, 
                        help="If you use this flag, program will log progress in greater detail."
                        )
    parser.add_argument('-T','--timezone',  default='local', 
                        help=
                        "You can use this flag to specify the timezone relative to which you want your results."
                        "\nThis is useful for when your organization is using a single formsite timezone for all subusers"
                        "\nInput either name of the timezone from this list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
                        "\nThe timezone database method accounts for daylight savings time."
                        "\nor an offset in the format +02:00 or +0200 or 0200 for a 2 hour later time (for example) from your LOCAL time"
                        "\n Offset    Cities (this does not account for daylight savings time)"
                        "\n'-12:00' - US minor outlying islands"
                        "\n'-11:00' - American Samoa, New Zealand"
                        "\n'-10:00' - Honolulu"
                        "\n'-09:00' - Anchorage"
                        "\n'-08:00' - Los Angeles, Vancouver, Tijuana"
                        "\n'-07:00' - Denver, Edmonton, Ciudad Juarez"
                        "\n'-06:00' - Mexico City, Chicago, San Salvador"
                        "\n'-05:00' - New York, Toronto, Havana, Lima"
                        "\n'-04:00' - Santiago, La Paz, Halifax"
                        "\n'-03:00' - São Paulo, Buenos Aires, Montevideo"
                        "\n'-02:00' - Atlantic East Islands"
                        "\n'-01:00' - Cape Verde, Greenland"
                        "\n'+00:00' - London, Lisbon, Dakar"
                        "\n'+01:00' - Berlin, Rome, Paris, Prague"
                        "\n'+02:00' - Cairo, Kiev, Jerusalem, Athens, Sofia"
                        "\n'+03:00' - Moscow, Istanbul, Baghdad, Addis Ababa"
                        "\n'+04:00' - Dubai, Tbilisi, Yerevan"
                        "\n'+05:00' - Karachi, Tashkent, Yekaterinburg"
                        "\n'+06:00' - Dhaka, Almaty, Omsk"
                        "\n'+07:00' - Jakarta, Ho Chi Minh City, Bangkok, Krasnoyarsk"
                        "\n'+08:00' - China - Shanghai, Taipei, Kuala Lumpur, Singapore, Perth, Manila, Makassar, Irkutsk"
                        "\n'+09:00' - Tokyo, Seoul, Pyongyang, Ambon, Chita"
                        "\n'+10:00' - Sydney, Port Moresby, Vladivostok"
                        "\n'+11:00' - Noumea, Magadan"
                        "\n'+12:00' - Auckland, Suva, Petropavlovsk-Kamchatsky"
                        )
    parser.add_argument('-F','--date_format',  default="%Y-%m-%d %H:%M:%S", 
                        help="Specify a quoted string using python datetime directives to specify what format you want your dates in (column: Date)."
                        "\nDefaults to '%%Y-%%m-%%d %%H:%%M:%%S' which is yyyy-mm-dd HH:MM:SS"
                        "\nYou can find the possible format directives here: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior"
                        )
    parser.add_argument('--download_type',  default="speedy", choices=('reliable,volume,sequential,speedy'),
                        help="You can specify --download_type volume to control how many concurrent downlaods can take place."
                        "\nreliable - 10 concurrent downloads (recommended for very large files)"
                        "\nspeedy - 50 concurrent downloads"
                        "\nvolume - unlimited concurrent downloads (!!! large files can time out)"
                        "\nsequential - only one download at a time"
                        )
    return parser.parse_known_args()

# Sanitizes user input
def __sanitize_arguments__(args):  
    if args.version == True: #If this flag is true, only handle displaying of version or possible updating
        pass
    else:
        quotes_map = [('\'',''), ('\"','')]
        
        args.username = __sanitize_checkrequired__(args.username,'username','-u','username',quotes_map)
        args.token = __sanitize_checkrequired__(args.token,'token','-t','token',quotes_map)
        args.form = __sanitize_checkrequired__(args.form,'form','-f','Nca894k',quotes_map)
        args.server = __sanitize_checkrequired__(args.server,'server','-s','fs1',quotes_map)
        args.directory = __sanitize_checkrequired__(args.directory,'directory','-d','Wa37fh',quotes_map)

        args.links_regex = __sanitize_checkrequired__(args.links_regex,'links_regex','-X','".+\.json$ to only get json files"',quotes_map)

        #args.afterref = int(args.afterref)
        #args.beforeref = int(args.beforeref)
        #args.afterdate = str(args.afterdate)
        #args.beforedate = str(args.beforedate)
        #args.resultslabels = int(args.resultslabels)
        #args.sort = str(args.sort)

        if args.output_file != False:
            args.output_file = __sanitize_unquote__(args.output_file,quotes_map)
            args.output_file = Path(args.output_file).resolve()
            if args.output_file.exists() == False:
                args.output_file.parent.mkdir(exist_ok =True, parents = True)
                args.output_file.touch()
            logging.log.debug(f"Output file: {args.output_file}")
        
        if args.extract_links != False:
            args.extract_links = __sanitize_unquote__(args.extract_links,quotes_map)
            args.extract_links = Path(args.extract_links).resolve()
            if args.extract_links.exists() == False:
                args.extract_links.parent.mkdir(exist_ok =True, parents = True)
                args.extract_links.touch()
            logging.log.debug(f"Links file: {args.extract_links}")
        
        if args.download_links != False:
            args.download_links = __sanitize_unquote__(args.download_links,quotes_map)
            args.download_links = Path(args.download_links).resolve()
            if args.download_links.exists() == False:
                Path.mkdir(args.download_links,parents=True,exist_ok=True)
            logging.log.debug(f"Download directory: {args.download_links}")
        
        #args.refresh_headers = bool(args.refresh_headers)
        #args.generate_results_files = bool(args.generate_results_files)
        #args.list_columns = bool(args.list_columns)
        #args.version = bool(args.version)
        #args.headers = bool(args.headers)
        #args.no_items = bool(args.no_items)
    return args

##              ##
## API  Methods ##
##              ##

# awaits response for results
async def __api_fetchContents_results__(response,page,stats,gen_files):
    logging.log.debug(f'API GET {response.status}: ({page}/{stats.num_pages})')
    contents = await response.content.read()
    return contents

# writes contents of response if necessary
async def __api_writeContents_results_(response,page,form_id,stats,gen_files):
    contents = await __api_fetchContents_results__(response,page,stats,gen_files)
    if gen_files == True:
        WriteFile(contents,f"results_{form_id}_{page}.json")
    return contents

# returns contents of response for results
async def __api_getResponse_results__(session,url,page,param,form_id,stats,gen_files):
    param['page'] = page
    async with session.get(url,params=param) as response:
        contents = await __api_writeContents_results_(response,page,form_id,stats,gen_files)
        if response.status != 200:
            logging.log.critical(f"Error {page}/{stats.num_pages}: {response.status}")
            logging.log.critical(json.loads(contents)['error'])
            quit()
        if page == 1:
            return contents,int(response.headers['Pagination-Page-Last'])
        else:
            return contents

# awaits response for items
async def __api_fetch_items__(response,form_id,gen_items):
    logging.log.debug(f'API GET {response.status}: (items)')
    contents = await response.content.read()
    return contents

# writes contents of response if necessary
async def __api_process_items__(response,form_id,gen_items):
    contents = await __api_fetch_items__(response,form_id,gen_items)
    if gen_items == True:
        WriteFile(contents,f"items_{form_id}.json")
    return contents

# returns contents of response for items
async def __api_response_items__(session,url,stats,param,form_id,gen_items):
    async with session.get(url,params=param) as response:
        contents = await __api_process_items__(response,form_id,gen_items)
        stats.itemsCalled += 1
        if response.status != 200:
            logging.log.critical(f"Error items: {response.status}")
            logging.log.critical(json.loads(contents)['error'])
            quit()
        return contents

# Starts processing items, won't process if items.json is already saved
async def __api_start_items__(args,session,url_items,stats,param_i):
    if args.refresh_headers == True:
        items = await __api_response_items__(session,url_items,stats,param_i,args.form,args.no_items)
    else:
        try:
            logging.log.debug(f"Reading contents from items_{args.form}.json")
            with open(f"items_{args.form}.json",'r') as rf:
                items = rf.read() 
        except:    
            items = await __api_response_items__(session,url_items,stats,param_i,args.form,args.no_items)
            stats.APIcount += 1
    return items

# Starts processing all API requests (both results and items) in a single aiohttp session
async def __api_StartProcessing__(url,auth,param_i,param_r,args,stats):
    url_results = f"{url}/results"
    url_items = f"{url}/items"
    t0 = time.perf_counter()
    logging.log.info("API: starting requests\n")
    results_list = []
    async with aiohttp.ClientSession(headers=auth) as session:
        if args.list_columns == False:
            first_result,stats.num_pages = await __api_getResponse_results__(session,url_results,1,param_r,args.form,stats,args.generate_results_files)
            max_batch = 48
            num_batches = int(stats.num_pages/max_batch)+1
            logging.log.info(f"Total requests: {stats.num_pages}")
            if int(stats.num_pages) > max_batch:
                logging.log.warning(f"This will exceed rate limit.\nThis will perform {stats.num_pages} calls. They will be split into {num_batches} batches, you will have to wait 1 minute between each batch.\nProceeding in 5 seconds.\n")
                time.sleep(5)
            results_list = [first_result.decode("utf-8")]
            for batch in range(0,num_batches):
                tasks = []
                response_list = []
                logging.log.info(f"Processing batch {batch+1} of requests")
                upper_bound=max_batch+batch*max_batch
                lower_bound=batch*max_batch
                if lower_bound == 0:
                    lower_bound=2
                if upper_bound >= stats.num_pages:
                    upper_bound=stats.num_pages+1
                for page in range(lower_bound,upper_bound):
                    response_array = asyncio.ensure_future(__api_getResponse_results__(session,url_results,page,param_r,args.form,stats,args.generate_results_files))
                    tasks.append(response_array)
                response_list_batch = await asyncio.gather(*tasks)
                for response in response_list_batch:
                    response = response.decode("utf-8")
                    results_list.append(response)
                if batch < num_batches-1:
                    logging.log.warning("Waiting 60 seconds...")
                    time.sleep(60)            
        t1 = time.perf_counter() - t0
        items = await __api_start_items__(args,session,url_items,stats,param_i)
        logging.log.info(f"API: processed all requests in {t1:0.2f} seconds\n")
        return results_list, items

# Loads headers from response or json file if present, returns json obejct
def __response2json_items__(itemsContent):
    try:
        itemsLoaded = json.loads(itemsContent)
        return itemsLoaded
    except:
        try:
            return json.loads(itemsContent)
        except:
            logging.log.critical("Error: Items could not be loaded as json, invalid format.")
            quit()

# Loads results from response(s), returns an array of json object(s)
def __response2json_results__(resultsResponse):
    try:
        resultsPageArray = []
        for result_page in resultsResponse:
            resultsPageArray.append(json.loads(result_page))
        return resultsPageArray
    except:
        logging.log.critical("Error: Results could not be loaded as json, invalid format.")
        quit()

# Renames hardcoded columns and moves them such that main_df_part1 is at beginning, then there is room for separated items, then main_df_part2
def __hardcoded_columns_renaming__(main_dataframe):
    main_df_part1 = main_dataframe[['id','result_status']]
    main_df_part1.columns = ['Reference #','Status']

    main_df_part2 = main_dataframe[['date_update','date_start','date_finish','duration','user_ip','user_browser','user_device','user_referrer']]
    main_df_part2.columns = ['Date','Start Time','Finish Time','Duration (s)','User','Browser','Device','Referrer']
    return main_df_part1,main_df_part2

# Creates and combines dataframes with hardcoded columns (excluding items)
def __combine_json_results__(json_list):
    df_array = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        r = executor.map(__results2df__,json_list)
    for i in r:
        df_array.append(i)
    return  pd.concat(df_array)

# Creates a dataframe from a json file for hardscoded columns
def __results2df__(json_result):
    return pd.DataFrame(json_result['results'],columns=['id','result_status','date_update','date_start','date_finish','duration','user_ip','user_browser','user_device','user_referrer'])

# Creates a dataframe from a json file for items
def __items2df__(json_items):
    return pd.DataFrame(json_items['results'])['items']

# Separates the items array for each submission in results into desired format
def __separate_items_single__(dataframe):
    list_of_rows = []
    for item in dataframe:
        one_row = []
        for i in item:
            textjoin = ""
            try:
                textjoin += i['value']
            except:
                for value in i['values']:
                    textjoin += value['value']
                    if len(i['values']) > 1:
                        textjoin += " | "
            one_row.append(textjoin)
        list_of_rows.append(one_row)
    return list_of_rows

# Performs item separation for array of json objects, calls __separate_items_single__()
def __separate_items_paginated__(json_list):
    df_array = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        r = executor.map(__items2df__,json_list)
    for i in r:
        df_array.append(i)
    return  __separate_items_single__(pd.concat(df_array))

# Returns an array of column labels to use for results - items
def __create_items_headers__(items_json):
    ih = pd.DataFrame(items_json['items'])['label']
    ih.name=None
    return ih.to_list()

# Checks if python version is greater than 2.7 and the script version, only informs
def __check_new_version__(check_new):
    if not sys.version_info >= (3, 4): #Check version
       logging.log.critical("Your version of python is not compatible with this script.\nPlease upgrade to python 3.4 or newer.")
       quit()
    current_version = "1.1.7"
    latest_version = ReadFile("https://raw.githubusercontent.com/strny0/formsite-utility/main/version.md")
    if check_new is True:
        logging.log.info(f"Your script version: {current_version}\nLatest version:    {latest_version}")
        update = input("Do you want to update to the latest version? (y/n)\n\n")
        if update.lower() == "y":
            DownloadFile(("https://raw.githubusercontent.com/strny0/formsite-utility/main/getform.py",f"getform-{latest_version}.py",1))
            logging.log.warning("Update complete, please run the new file instead.")
        quit()
    if current_version != latest_version:
        logging.log.info(f"Your script version: {current_version}\nLatest version:    {latest_version}")
        logging.log.info("You can include the -V flag to update next time you launch this program.")
        time.sleep(3)
        
# Shifts input date by timezone offset, if you provided -T argument
def __shift_param_date__(date,timezone_offset):
    try:
        date = dt.strptime(date,"%Y-%m-%dT%H:%M:%SZ")
    except: 
        try:
            date = dt.strptime(date,"%Y-%m-%d")
        except:
            try:
                date = dt.strptime(date,"%Y-%m-%d %H:%M:%S")
            except:
                logging.log.critical('invalid date format input for afterdate/beforedate, please use ISO 8601, yyyy-mm-dd or yyyy-mm-dd HH:MM:SS')
                quit()
    date = date - timezone_offset
    date = dt.strftime(date,"%Y-%m-%dT%H:%M:%SZ")
    return date

# Generates a dictionary of parameters for results API request
def __generate_header_results__(args):
    resultsParams = dict()
    # Results params
    colID_sort = 0 # which column it sorts by
    colID_equals = 0 # which column it looks into with equals search param
    colID_contains = 0 # which column it looks into with contains search param
    colID_begins = 0 # which column it looks into with begins search param
    colID_ends = 0 # which column it looks into with ends search param
    paramSearch_equals = ''
    paramSearch_contains = ''
    paramSearch_begins = ''
    paramSearch_ends = ''
    paramSearch_method = ''

    logging.log.info("getform.py started with the following arguments:")
    # Results header creation
    resultsParams = dict()
    resultsParams['limit'] = 500 # 500 = max allowed size
    if args.afterref != 0:
        resultsParams['after_id'] = args.afterref
        logging.log.info(f"afterref: {args.afterref}")
    if args.beforeref != 0:
        resultsParams['before_id'] = args.beforeref
        logging.log.info(f"beforeref: {args.beforeref}")
    if args.afterdate != "":
        args.afterdate = __shift_param_date__(args.afterdate,args.timezone)
        resultsParams['after_date'] = args.afterdate
        logging.log.info(f"afterdate: {args.afterdate}")
    if args.beforedate != "":
        args.beforedate = __shift_param_date__(args.beforedate,args.timezone)
        resultsParams['before_date'] = args.beforedate
        logging.log.info(f"beforedate: {args.beforedate}")
    resultsParams['sort_direction'] = args.sort
    logging.log.info(f"sort_direction: {args.sort}")
    resultsParams['results_view'] = 11 # 11 = all items + statistics
    logging.log.info(f"results_view: 11")
    if colID_sort != 0:
        resultsParams['sort_id'] = colID_sort
        logging.log.info(f"sort_id: {colID_sort}")
    if colID_equals != 0 or paramSearch_equals != '':
        resultsParams[f'search_equals[{colID_equals}] ='] = paramSearch_equals
        logging.log.info(f"colID_equals: {colID_equals}")
    if colID_contains != 0 or paramSearch_contains != '':
        resultsParams[f'search_contains[{colID_contains}] ='] = paramSearch_contains
        logging.log.info(f"search_contains: {colID_contains}")
    if colID_begins != 0 or paramSearch_begins != '':
        resultsParams[f'search_begins[{colID_begins}] ='] = paramSearch_begins
        logging.log.info(f"colID_begins: {colID_begins}")
    if colID_ends != 0 or paramSearch_ends != '':
        resultsParams[f'search_ends[{colID_ends}] ='] = paramSearch_ends
        logging.log.info(f"colID_ends: {colID_ends}")
    if paramSearch_method != '':
        resultsParams['search_method'] = paramSearch_method
        logging.log.info(f"search_method: {paramSearch_method}")
    return resultsParams

# Generates a dictionary for API authorization purposes from username and token
def __generate_header_auth__(args):
    authHeader = {"Authorization": args.username+" " +
                  args.token, "Accept": "application/json"}
    logging.log.debug(f'Authorization HTTP header generated')
    return authHeader

# If -x argument is added, writes links into a file of specified location.
def WriteLinks(link_array, filename):
    logging.log.debug(f"Writing links into: {filename}")
    with open(filename,'w',encoding="utf-8") as links_file:
        for link in link_array:
            links_file.write(link+"\n")

# This function triggers the file download process for a list of links.
def DownloadFormsiteLinks(links, files_url, args):
    logging.log.info(f"Starting download of {len(links)} files...\n")
    t0 = time.perf_counter()
    try:
        os.mkdir(args.download_links)
        logging.log.debug(f"Creating {args.download_links.as_posix()}")
    except:
        logging.log.debug(f"Directory {args.download_links.as_posix()} already exists.")
    
    arg_list = [(i,args.download_links.as_posix()+"/"+i.replace(files_url,""),1) for i in links]
    if args.download_type == "volume":
        MAX_WORKERS = int(len(links))
    elif args.download_type == "speedy":
        MAX_WORKERS = 50
    elif args.download_type == "sequential":
        MAX_WORKERS = 1
    elif args.download_type == "reliable":
        MAX_WORKERS = 10
    else:
        MAX_WORKERS = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(DownloadFile,arg_list)

    t = time.perf_counter() - t0
    logging.log.info(f"{len(links)} files downloaded in in {t:0.2f} seconds\n")
    
# This function writes the file to storage.
def WriteFile(content, filename, attempt=1,attempts=10):
    try:
        logging.log.debug(f"WRITING:         {filename}")
        with open(filename,'wb') as wf:
            wf.write(content)
    except:
        logging.log.critical(f"({attempt}/{attempts}) Error writing file {filename}    Trying again...")
        attempt += 1
        if attempt >= attempts:
            logging.log.info(f"Failed to write {filename} after {attempt} attempts...")
            exit()
        else:
            WriteFile(content, filename, attempt)

# This function triggers the download and the writing of the file.
def DownloadFile(arg,attempts=10):
    try:
        content = FetchFile(arg[0])
        WriteFile(content, arg[1],arg[2])
    except:
        logging.log.critical(f"({arg[2]}/{attempts}) Error downloading file {arg[0]}    Trying again...")
        attempt = arg[2]+1
        arg = (arg[0],arg[1],attempt)
        if attempt >= attempts:
            logging.log.info(f"Failed to download {arg[0]} after {attempt} attempts...")
            exit()
        else:
            DownloadFile(arg)

# This function downloads a file but doesn't write it, only returns its content
def ReadFile(url):
    try:
        content = FetchFile(url)
        return content.decode('utf-8')
    except:
        logging.log.info(f"Could not read: {url}")
        return None
  
# A part of the downloads file function. This async function downloads the file to memory.
def FetchFile(url, attempt=1,attempts=10):
    logging.log.debug(f"QUEUED DOWNLOAD: {url}")
    try:
        with requests.get(url) as response:
            content = response.content
        logging.log.debug(f"DOWNLOADED:      {url}")
        return content
    except:
        logging.log.debug(f"({attempt}/{attempts}) Error downloading {url}")
        attempt += 1
        if attempt >= attempts:
            logging.log.info(f"Failed to download {url} after {attempt} attempts...")
            exit()
        else:
            FetchFile(url, attempt=attempt)

# If -l argumant is added, will output a more readable version of the items.json of requested form
def ListColumns(itemsResponseContent):
    itemsLoaded = __response2json_items__(itemsResponseContent)
    items_index = 0
    print("This is a list of all columns - id pairs:")
    while items_index < len(itemsLoaded['items']):
        print(f"{itemsLoaded['items'][items_index]['id']}:   {itemsLoaded['items'][items_index]['label']}")
        items_index += 1
        continue
    logging.log.info('API request count: %d' % statistics.APIcount)

# Class that stores useful information
class Stats:
    num_pages = '?'
    APIcount = 0
    lmAPI = 0
    itemsCalled = 0

#Convert Dates to datetime if inputed in UTC ISO 8601 format
def __string2datetime__(old_date,timezone_offset):
    try:    
        new_date = dt.strptime(old_date,"%Y-%m-%dT%H:%M:%S"+"Z")
        new_date = new_date - timezone_offset
        return new_date
    except:
        return old_date

# This method handles the -o flag, writes either an excel, json or CSV file
def WriteResults(args, dataframe, encoding, separator, line_terminator, date_format,base_date):
    if args.output_file != False:
        logging.log.info("Writing final report...\n")
        if arguments.output_file == Path.cwd().resolve():
            output_file = "export_%s_%s.csv" % (args.form,dt.strftime(base_date,date_format))
        else:
            output_file = args.output_file.resolve().as_posix()
        if regex.search('.+\\.xlsx$', output_file) is not None:
            dataframe.to_excel(output_file,index=False,encoding=encoding)
        elif regex.search('.+\\.json$', output_file) is not None:
            dataframe.to_json(output_file, orient="records")
        else:
            dataframe.to_csv(output_file,sep=separator,index=False,encoding=encoding,line_terminator=line_terminator,date_format=args.date_format)

        logging.log.info('Export:    %s'  % output_file)
        logging.log.info('Rows:      %d ' % len(dataframe.index))
        logging.log.info('Cols:      %d ' % len(dataframe.columns))
        logging.log.info('Encoding:  %s\n'  % encoding)
        
# Removes quotes from a provided string, returns unquoted string
def __sanitize_unquote__(argument,chars2remove):
    for k,v in chars2remove:
        argument = str(argument).replace(k,v)
    return argument

# Checks if data put into certain argparse arguments is correct
def __sanitize_checkrequired__(argument,argument_name,flag,example,quotes):
    if argument == None:
        logging.log.critical(f"Missing {argument_name}. Please use the {flag} flag to enter your argument. ex: {flag} {example}")
        quit()
    argument = __sanitize_unquote__(argument,quotes)
    return argument

# Custom logging class
class __logger__:                                                                     
    def __init__(self, is_verbose=False):                                       
        # configuring log                                                       
        if (is_verbose):                                                        
            self.log_level=logging.DEBUG   
            log_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        else:                                                                   
            self.log_level=logging.INFO          
            log_format = logging.Formatter('%(message)s')

        self.log = logging.getLogger(__name__)                                  
        self.log.setLevel(self.log_level)                                       
        # writing to stdout                                                     
        handler = logging.StreamHandler(sys.stdout)                             
        handler.setLevel(self.log_level)                                        
        handler.setFormatter(log_format)                                        
        self.log.addHandler(handler)       
        self.log.debug('Outputting logs in DEBUG mode.')                                     

# Generates timezone offset as a timedelta of your local timezone and your input timezone
def __get_timezone_offset__(args):
    local_date = dt.now()
    if regex.search(r'(\+|\-|)([01]?\d|2[0-3])([0-5]\d)',args.timezone) is not None:
        inp = args.timezone.replace("'","")
        inp = [inp[:2],inp[2:]] if len(inp)==4 else [inp[:3],inp[3:]]
        offset_from_local = td(hours=int(inp[0]),seconds=int(inp[1])/60)
    elif regex.search(r'(\+|\-|)([01]?\d|2[0-3]):([0-5]\d)',args.timezone) is not None:
        inp = args.timezone.replace("'","")
        inp = [inp[:2],inp[3:]] if len(inp)==5 else [inp[:3],inp[4:]]
        offset_from_local = td(hours=int(inp[0]),seconds=int(inp[1])/60)
    elif regex.search(r'.+/.+',args.timezone) is not None:
        try:
            inp = pytz.timezone(args.timezone).localize(local_date).strftime("%z")
            inp = [inp[:2],inp[2:]] if len(inp)==4 else [inp[:3],inp[3:]]
            offset_from_local = td(hours=int(inp[0]),seconds=int(inp[1])/60)
        except:
            logging.log.critical("Invalid timezone format provided")
            quit()
    elif args.timezone == 'local':
        offset_from_local = td(seconds=0)
    else:
        logging.log.critical("Invalid timezone format provided")
        quit()

    
    logging.log.info(f'Starting formsite extraction on: {local_date.strftime("%Y-%m-%d %H:%M:%S")}')
    logging.log.info(f'Timezone offset (from local timezone) is: {offset_from_local.total_seconds()/60/60} hours')
    return offset_from_local, local_date

# Program
if __name__ == '__main__':
    # Set up arguments from CLI input and some other initial vars
    statistics = Stats()
    arguments = __setup_arguments__()[0] # 0th index is argparse arguments, other are arguments not recognized by argparser
    
    # Configures logging.log options
    logging = __logger__(arguments.verbose)

    # Unquotes arguments, checks if they are parsed correctly
    arguments = __sanitize_arguments__(arguments)

    #If -T was used, calculates timedelta timezone offset
    arguments.timezone, base_date = __get_timezone_offset__(arguments)

    # Checks for python version and program version
    __check_new_version__(arguments.version)

    # Generates initial variables from argparse arguments provided
    url_base=f"https://{arguments.server}.formsite.com/api/v2/{arguments.directory}"
    url_files=f"https://{arguments.server}.formsite.com/{arguments.directory}/files/"
    url_forms=f"{url_base}/forms/{arguments.form}/"

    # Generates headers for parametrs for API results request, used in function below
    authHeader = __generate_header_auth__(arguments)
    resultsParams = __generate_header_results__(arguments)

    itemsParams = {"results_labels":arguments.resultslabels}
    logging.log.info(f"results_labels: {arguments.resultslabels}")

    # Asynchronous API calls
    loop = asyncio.get_event_loop() # if i close this i get an error, idk...
    future = asyncio.ensure_future(__api_StartProcessing__(url_forms,authHeader,itemsParams,resultsParams,arguments,statistics))
    resultsContent_List,itemsContent = loop.run_until_complete(future)
    #resultsContent_List,itemsContent = asyncio.run(__api_StartProcessing__(url_forms,authHeader,itemsParams,resultsParams,arguments,statistics))
    # This code will get executed if you provide the -l argument
    if arguments.list_columns is True:
        ListColumns(itemsContent)
        quit()
    
    # Load downloaded json files
    tp0 = time.perf_counter()
    logging.log.info("Processing results...")
    items_LoadedObject = __response2json_items__(itemsContent) 
    results_LoadedObject = __response2json_results__(resultsContent_List)

        # If there are no results in parameters specified, quit program.
    if len(results_LoadedObject[0]['results']) == 0:
        logging.log.critical("There are no results in specified parameters.")
        quit()
    
    # Create main dataframe with Results Responses Jsons
    HardCodedDF = __combine_json_results__(results_LoadedObject)
    ItemsDF = pd.DataFrame(__separate_items_paginated__(results_LoadedObject),columns=__create_items_headers__(items_LoadedObject))

    # Convert date formats from ISO 8601 TO MM/DD/YYYY hh:mm:ss and sets other formats that usually get generated when exporting
    HardCodedDF['date_update'] = HardCodedDF['date_update'].apply(lambda x: __string2datetime__(x,arguments.timezone))
    HardCodedDF['date_start'] = HardCodedDF['date_start'].apply(lambda x: __string2datetime__(x,arguments.timezone))
    HardCodedDF['date_finish'] = HardCodedDF['date_finish'].apply(lambda x: __string2datetime__(x,arguments.timezone))
    HardCodedDF['duration'] = HardCodedDF['date_finish'] - HardCodedDF['date_start']
    HardCodedDF['duration'] = HardCodedDF['duration'].apply(lambda x: x.total_seconds())

    # Merges dataframes into a final structure
    df_1,df_2 = __hardcoded_columns_renaming__(HardCodedDF.reset_index(drop=True))
    FullDataframe = pd.concat([df_1, ItemsDF, df_2], axis=1)
    tp1 = time.perf_counter() - tp0
    logging.log.info(f"Formsite data processed in {tp1:0.2f} seconds...")
    # Write EXCEL/JSON/CSV from constructed array
    WriteResults(arguments, FullDataframe, 'utf-8', ',', '\n', "%Y-%m-%d--%H-%M-%S%z",base_date)
    
    # Special case of option -x or -D
    if arguments.extract_links != False or arguments.download_links != False:
        temp_df = FullDataframe
        temp_df.columns = [n for n in range(0,len(temp_df.columns))]
        links = []
        logging.log.info("Extracting links...")
        for col in temp_df.columns:
            txt = temp_df[col].to_list()
            try:
                for item in txt:
                    if item.startswith(url_files) == True:
                        if regex.search(arguments.links_regex,item) is not None:
                            links.append(item)
            except:
                continue
        if arguments.extract_links != False:
            if arguments.extract_links == Path.cwd():
                x_filename = f"links_{arguments.form}_{base_date.strftime('%Y-%m-%d--%H-%M-%S%z')}.txt"
            else:
                x_filename = arguments.extract_links
            WriteLinks(links,x_filename)
            logging.log.info(f"Formsite download links extracted:    {x_filename}\n")
        if arguments.download_links != False:
            DownloadFormsiteLinks(links,url_files,arguments)
    # End
    logging.log.info('API calls: %d' % (int(statistics.num_pages)+int(statistics.itemsCalled)))
    quit()