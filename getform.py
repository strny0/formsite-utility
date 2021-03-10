#!/usr/bin/python3
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

from sys import version_info #s         #s - standard library, #! - 3rd party module
from datetime import datetime as dt #s
import time #s
from io import open as open #s
import os #s
from pathlib import Path as Path #s
import json #s
import csv #s
import argparse #s

import pytz #1
import regex #!
import asyncio #!
import aiohttp #!
import pandas as pd #!
import openpyxl #!

##              ##
## API  Methods ##
##              ##
    
async def fetchContents_Results(verbose,response,page,stats,gen_files):
    print(f'API GET {response.status}: ({page}/{stats.num_pages})') if verbose else 0
    contents = await response.content.read()
    return contents

async def processResponse_Results(verbose,response,page,form_id,stats,gen_files):
    contents = await fetchContents_Results(verbose,response,page,stats,gen_files)
    if gen_files == True:
        await WriteFile_async(contents,f"results_{form_id}_{page}.json")
    return contents

async def getResponseContents_Result(verbose,session,url,page,param,form_id,stats,gen_files):
    param['page'] = page
    async with session.get(url,params=param) as response:
        contents = await processResponse_Results(verbose,response,page,form_id,stats,gen_files)
        if response.status != 200:
            print(f"Error {page}/{stats.num_pages}: {response.status}")
            print(json.loads(contents)['error'])
            quit()
        if page == 1:
            return contents,int(response.headers['Pagination-Page-Last'])
        else:
            return contents

async def fetchContents_Items(verbose,response,form_id,gen_items):
    print(f'API GET {response.status}: (items)') if verbose else 0
    contents = await response.content.read()
    return contents

async def processResponse_Items(verbose,response,form_id,gen_items):
    contents = await fetchContents_Items(verbose,response,form_id,gen_items)
    if gen_items == True:
        await WriteFile_async(contents,f"items_{form_id}.json",verbose)
    return contents

async def getResponseContents_Items(verbose,session,url,stats,param,form_id,gen_items):
    async with session.get(url,params=param) as response:
        contents = await processResponse_Items(verbose,response,form_id,gen_items)
        if response.status != 200:
            print(f"Error items: {response.status}")
            print(json.loads(contents)['error'])
            quit()
        return contents

async def processItems(args,session,url_items,stats,param_i):
    if args.refresh_headers == True:
        items = await getResponseContents_Items(args.verbose,session,url_items,stats,param_i,args.form,args.no_items)
    else:
        try:
            print(f"Reading contents from items_{args.form}.json") if args.verbose == True else 0
            with open(f"items_{args.form}.json",'r') as rf:
                items = rf.read() 
        except:    
            items = await getResponseContents_Items(args.verbose,session,url_items,stats,param_i,args.form,args.no_items)
    return items

async def performAPIrequests(url,auth,param_i,param_r,args,stats):
    url_results = f"{url}/results"
    url_items = f"{url}/items"
    t0 = time.perf_counter()
    print("API: starting requests")
    async with aiohttp.ClientSession(headers=auth) as session:
        if args.list_columns == False:
            first_result,stats.num_pages = await getResponseContents_Result(args.verbose,session,url_results,1,param_r,args.form,stats,args.generate_results_files)
            max_batch = 48
            num_batches = int(stats.num_pages/max_batch)+1
            print(f"Total requests: {stats.num_pages}")
            if int(stats.num_pages) > max_batch:
                print(f"Warning, this will exceed rate limit.\nThis will perform {stats.num_pages} calls. They will be split into {num_batches} batches, you will have to wait 1 minute between each batch.\nProceeding in 5 seconds.")
                time.sleep(5)
            results_list = [first_result.decode("utf-8")]
            for batch in range(0,num_batches):
                tasks = []
                response_list = []
                print(f"Processing batch {batch+1} of requests")
                upper_bound=max_batch+batch*max_batch
                lower_bound=batch*max_batch
                if lower_bound == 0:
                    lower_bound=2
                if upper_bound >= stats.num_pages:
                    upper_bound=stats.num_pages+1
                for page in range(lower_bound,upper_bound):
                    response_array = asyncio.ensure_future(getResponseContents_Result(args.verbose,session,url_results,page,param_r,args.form,stats,args.generate_results_files))
                    tasks.append(response_array)
                response_list_batch = await asyncio.gather(*tasks)
                for response in response_list_batch:
                    response = response.decode("utf-8")
                    results_list.append(response)
                if batch < num_batches-1:
                    print("Waiting 60 seconds...")
                    time.sleep(60)            
        t1 = time.perf_counter() - t0
        items = await processItems(args,session,url_items,stats,param_i)
        print(f"API: processed all requests in {t1:0.2f} seconds")
        return results_list, items

# Loads headers from response or json file if present, returns json obejct
def LoadItemsAsJsonObject(itemsContent):
    try:
        itemsLoaded = json.loads(itemsContent)
        return itemsLoaded
    except:
        try:
            return json.loads(itemsContent)
        except:
            print("Error: Items could not be loaded as json, invalid format.")
            exit

# Loads results from response(s), returns an array of json object(s)
def LoadResultsAsJsonObject(resultsResponse):
    try:
        resultsPageArray = []
        for result_page in resultsResponse:
            resultsPageArray.append(json.loads(result_page))
        return resultsPageArray
    except:
        print("Error: Results could not be loaded as json, invalid format.")
        quit()

# Check if API error exists in response. If yes, outputs the error.
def CheckIfAPIerrorExists(anyResponse):
    try:
        jsonObject = anyResponse.json()['error']
        print("ERR:    %s : %s" % (jsonObject['status'],jsonObject['message']))
        return True
    except:
        return False

# Renames hardcoded columns and moves them such that main_df_part1 is at beginning, then there is room for separated items, then main_df_part2
def RenameHardcodedCols(main_dataframe):
    main_df_part1 = main_dataframe[['id','result_status']]
    main_df_part1.columns = ['Reference #','Status']

    main_df_part2 = main_dataframe[['date_update','date_start','date_finish','duration','user_ip','user_browser','user_device','user_referrer']]
    main_df_part2.columns = ['Date','Start Time','Finish Time','Duration (s)','User','Browser','Device','Referrer']
    return main_df_part1,main_df_part2

# Creates and combines dataframes with hardcoded columns (excluding items)
def CreateMainDataframe(array_of_json_results):
    df_array = []
    for json_result in array_of_json_results:
        df_instance = pd.DataFrame(json_result['results'],columns=['id','result_status','date_update','date_start','date_finish','duration','user_ip','user_browser','user_device','user_referrer'])
        df_array.append(df_instance)
    return  pd.concat(df_array)

# Separates the items array for each submission in results into desired format
def SeparateItems(dataframe):
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

# Performs item separation for array of json objects
def SeparatePaginatedItems(array_of_json_results):
    df_array = []
    for json_result in array_of_json_results:
        df_instance = pd.DataFrame(json_result['results'])['items']
        df_array.append(df_instance)
    return  SeparateItems(pd.concat(df_array))

# Returns an array of column labels to use for results - items
def CreateItemsHeaders(items_json):
    ih = pd.DataFrame(items_json['items'])['label']
    ih.name=None
    return ih.to_list()

# Checks if python version is greater than 2.7 and the script version, only informs
def CheckVersion(check_new,event_loop,verbose):
    if not version_info >= (3, 4): #Check version
       print("Your version of python is not compatible with this script.\nPlease upgrade to python 3.4 or newer.")
       quit()
    current_version = "1.1.4"
    future = asyncio.ensure_future(GetNewVersion("https://raw.githubusercontent.com/strny0/formsite-utility/main/version.md",verbose))
    latest_version = event_loop.run_until_complete(future)
    if current_version != latest_version:
        print(f"Your script version: {current_version}\nLatest version:    {latest_version}")
        print("You can include the -V flag to update next time you launch this program.")
        time.sleep(3)
    if check_new is True:
        print(f"Your script version: {current_version}\nLatest version:    {latest_version}")
        update = input("Do you want to update to the latest version? (y/n)\n")
        if update.lower() == "y":
            future = asyncio.ensure_future(StartFileDownload(f"getform-{latest_version}.py","https://raw.githubusercontent.com/strny0/formsite-utility/main/getform.py",verbose))
            event_loop.run_until_complete(future)
            print("\nUpdate complete, please run the new file instead.")
        quit()
        
# Checks python version and also check version.md on github for latest pushed version. Lets user know of available updates.
async def GetNewVersion(version_url,verbose):
    async with aiohttp.ClientSession() as session:
        content = await ReadFile_async(session,version_url,verbose)
        return content

# Asynchronously downloads a file
async def StartFileDownload(filename,url,verbose):
    async with aiohttp.ClientSession() as session:
        await DownloadFile_async(session, filename,url,verbose)

#           #
#  PROMPTS  #
#           #

def SetupArgumentParser(): # Sets parameters/arguments getform.py takes
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
    parser.add_argument('-D', '--download_links', nargs='?',  default=False, const=Path.cwd().joinpath(f'./download_{dt.now().strftime("%Y-%m-%d--%H-%M-%S%z")}'),
                        help="If you include this flag, all formsite links in the export will be downloaded to a folder. \nYou can specify location, for example `-D 'C:\\Users\\My Username\\Desktop\\downloads'` . \nIf you don't specify a location, it will default to the folder of the script."
                        )
    parser.add_argument('--sort', choices=['asc', 'desc'], type=str,  default="desc", 
                        help="Determines how the output CSV will be sorted. Defaults to descending."
                        )
    parser.add_argument('-l', '--list_columns', action="store_true",  default=False, 
                        help="If you use this flag, program will output mapping of what column belongs to which column ID instead of actually running, \nuseful for figuring out search arguments.\n"
                        )
    parser.add_argument('-g', '--generate_results_files', action="store_true",  default=False, 
                        help="If you use this flag, program will output raw results in json format from API requests. \nUseful for debugging purposes."
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
                        "\nInput either string that describes your timezone such as UTC, CET, ART, GMT, MST, EST, etc. or an offset in the format +02:00"
                        "\n(there are many abbreviations for the same timezones, you can pick any abbreviation)"
                        "\n Offset   Abbrev. Cities"
                        "\n'-12:00' - IDLW - US minor outlying islands"
                        "\n'-11:00' - SST  - American Samoa, New Zealand"
                        "\n'-10:00' - HST  - Honolulu"
                        "\n'-09:00' - HDT  - Anchorage"
                        "\n'-08:00' - PST  - Los Angeles, Vancouver, Tijuana"
                        "\n'-07:00' - MST  - Denver, Edmonton, Ciudad Juaréz"
                        "\n'-06:00' - CST  - Mexico City, Chicago, San Salvador"
                        "\n'-05:00' - EST  - New York, Toronto, Havana, Lima"
                        "\n'-04:00' - CLT  - Santiago, La Paz, Halifax"
                        "\n'-03:00' - ART  - São Paulo, Buenos Aires, Montevideo"
                        "\n'-02:00' - BRST - Atlantic East Islands"
                        "\n'-01:00' - CVT  - Cape Verde, Greenland"
                        "\n'+00:00' - UTC  - London, Lisbon, Dakar"
                        "\n'+01:00' - CET  - Berlin, Rome, Paris, Prague"
                        "\n'+02:00' - EET  - Cairo, Kiev, Jerusalem, Athens, Sofia"
                        "\n'+03:00' - EEST - Moscow, Istanbul, Baghdad, Addis Ababa"
                        "\n'+04:00' - VOLT - Dubai, Tbilisi, Yerevan"
                        "\n'+05:00' - YEKT - Karachi, Tashkent, Yekaterinburg"
                        "\n'+06:00' - OMST - Dhaka, Almaty, Omsk"
                        "\n'+07:00' - CXT  - Jakarta, Ho Chi Minh City, Bangkok, Krasnoyarsk"
                        "\n'+08:00' - CST  - Shanghai, Taipei, Kuala Lumpur, Singapore, Perth, Manila, Makassar, Irkutsk"
                        "\n'+09:00' - JST  - Tokyo, Seoul, Pyongyang, Ambon, Chita"
                        "\n'+10:00' - AEST - Sydney, Port Moresby, Vladivostok"
                        "\n'+11:00' - NFT  - Nouméa, Magadan"
                        "\n'+12:00' - NZST - Auckland, Suva, Petropavlovsk-Kamchatsky"
                        )
    return parser.parse_known_args()

# Generates a dictionary of parameters for results API request
def GenerateResultsHeader(args):
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

    # Results header creation
    resultsParams = dict()
    resultsParams['limit'] = 500 # 500 = max allowed size
    if args.afterref != 0:
        resultsParams['after_id'] = args.afterref
        print(f"afterref: {args.afterref}")
    if args.beforeref != 0:
        resultsParams['before_id'] = args.beforeref
        print(f"beforeref: {args.beforeref}")
    if args.afterdate != "":
        resultsParams['after_date'] = args.afterdate
        print(f"afterdate: {args.afterdate}")
    if args.beforedate != "":
        resultsParams['before_date'] = args.beforedate
        print(f"beforedate: {args.beforedate}")
    resultsParams['sort_direction'] = args.sort
    print(f"sort_direction: {args.sort}") if args.verbose == True else 0
    resultsParams['results_view'] = 11 # 11 = all items + statistics
    print(f"results_view: 11") if args.verbose == True else 0
    if colID_sort != 0:
        resultsParams['sort_id'] = colID_sort
        print(f"sort_id: {colID_sort}")
    if colID_equals != 0 or paramSearch_equals != '':
        resultsParams[f'search_equals[{colID_equals}] ='] = paramSearch_equals
        print(f"colID_equals: {colID_equals}")
    if colID_contains != 0 or paramSearch_contains != '':
        resultsParams[f'search_contains[{colID_contains}] ='] = paramSearch_contains
        print(f"search_contains: {colID_contains}")
    if colID_begins != 0 or paramSearch_begins != '':
        resultsParams[f'search_begins[{colID_begins}] ='] = paramSearch_begins
        print(f"colID_begins: {colID_begins}")
    if colID_ends != 0 or paramSearch_ends != '':
        resultsParams[f'search_ends[{colID_ends}] ='] = paramSearch_ends
        print(f"colID_ends: {colID_ends}")
    if paramSearch_method != '':
        resultsParams['search_method'] = paramSearch_method
        print(f"search_method: {paramSearch_method}")
    return resultsParams

# Generates a dictionary for API authorization purposes from username and token
def GenerateAuthHeader(args):
    authHeader = {"Authorization": args.username+" " +
                  args.token, "Accept": "application/json"}
    return authHeader

# If -x argument is added, writes links into a file of specified location.
def WriteLinks(link_array, filename,verbose):
    print(f"Writing links into: {filename}") if verbose == True else 0
    with open(filename,'w',encoding="utf-8") as links_file:
        for link in link_array:
            links_file.write(link+"\n")

# A part of the async downloads file function. This async function downloads the file to memory.
async def FetchFile_async(session,url,verbose):
    print(f"DOWNLOADING: {url}") if verbose == True else 0
    async with session.get(url) as response:
        content = await response.read()
    return content

# This async function writes the file to storage.
async def WriteFile_async(content, filename, verbose):
    print(f"WRITING:     {filename}") if verbose == True else 0
    with open(filename,'wb') as wf:
        wf.write(content)

# This async function triggers the download and the writing of the file.
async def DownloadFile_async(session,filename, url, verbose):
    try:
        content = await FetchFile_async(session,url, verbose)
        await WriteFile_async(content, filename, verbose)
    except:
        print(f"Error downloading/writing {filename}")

# This async function downloads a file but doesn't write it, only returns its content
async def ReadFile_async(session,url,verbose):
    content = await FetchFile_async(session,url,verbose)
    return content.decode('utf-8')

# This async function triggers the file download process for a list of links.
async def FileDownloadLoop(links, files_url, args):
    print(f"Starting download of {len(links)} files...")
    tasks = []
    t0 = time.perf_counter()
    try:
        os.mkdir(args.download_links)
        print(f"Creating {args.download_links.as_posix()}") if args.verbose == True else 0
    except:
        print(f"Directory {args.download_links.as_posix()} already exists.") if args.verbose == True else 0
    async with aiohttp.ClientSession() as session:
        for url in links:
            filename = args.download_links.as_posix()+"/"+url.replace(files_url,'')
            tasks.append(DownloadFile_async(session,filename,url,args.verbose))
        await asyncio.gather(*tasks)
    t = time.perf_counter() - t0
    print(f"{len(links)} files downloaded in in {t:0.2f} seconds\n")

# If -l argumant is added, will output a more readable version of the items.json of requested form
def ListColumns(itemsResponseContent):
    itemsLoaded = LoadItemsAsJsonObject(itemsResponseContent)
    items_index = 0
    print("This is a list of all columns - id pairs:")
    while items_index < len(itemsLoaded['items']):
        print(f"{itemsLoaded['items'][items_index]['id']}:   {itemsLoaded['items'][items_index]['label']}")
        items_index += 1
        continue
    print('API request count: %d' % statistics.APIcount)

# Class that stores useful information
class Stats:
    num_pages = '?'
    APIcount = 0
    lmAPI = 0

#Convert Dates to datetime if inputed in UTC ISO 8601 format
def FixDates(iso_date):
    try:    
        new_date = dt.strptime(iso_date,"%Y-%m-%dT%H:%M:%S"+"Z")
        return new_date
    except:
        return iso_date

# This method handles the -o flag, writes either an excel, json or CSV file
def WriteResults(args, dataframe, encoding, separator, line_terminator, quoting, date_format):
    if args.output_file != False:
        print("Writing final report...")
        if arguments.output_file == Path.cwd().resolve():
            output_file = "%s_export_%s.csv" % (dt.strftime(dt.now(),date_format),args.form) # "%Y-%m-%d %H-%M-%S"
        else:
            output_file = args.output_file.resolve().as_posix()
        if regex.search('.+\\.xlsx$', output_file) is not None:
            dataframe.to_excel(output_file,index=False,encoding=encoding)
        elif regex.search('.+\\.json$', output_file) is not None:
            dataframe.to_json(output_file, orient="records")
        else:
            dataframe.to_csv(output_file,sep=separator,index=False,encoding=encoding,quoting=quoting,line_terminator=line_terminator)

        print('Export:    %s'  % output_file)
        print('Rows:      %d ' % len(dataframe.index))
        print('Cols:      %d ' % len(dataframe.columns))
        print('Encoding:  %s'  % encoding)
        
# Removes quotes from a provided string, returns unquoted string
def UnquoteString(argument,quotes):
    for k,v in quotes:
        argument = str(argument).replace(k,v)
    return argument

# Checks if data put into certain argparse arguments is correct
def CheckGroupA(argument,argument_name,flag,example,quotes):
    if argument == None:
        print(f"Missing {argument_name}. Please use the {flag} flag to enter your username. ex: {flag} {example}")
        quit()
    argument = UnquoteString(argument,quotes)
    return argument

# Sanitizes user input
def SanitizeArguments(args):  
    if args.version == True: #If this flag is true, only handle displaying of version or possible updating
        pass
    else:
        quotes_map = [('\'',''), ('\"','')]
        
        args.username = CheckGroupA(args.username,'username','-u','username',quotes_map)
        args.token = CheckGroupA(args.token,'token','-t','token',quotes_map)
        args.form = CheckGroupA(args.form,'form','-f','Nca894k',quotes_map)
        args.server = CheckGroupA(args.server,'server','-s','fs1',quotes_map)
        args.director = CheckGroupA(args.directory,'directory','-d','Wa37fh',quotes_map)

        args.links_regex = CheckGroupA(args.links_regex,'links_regex','-X','".+\.json$ to only get json files"',quotes_map)

        #args.afterref = int(args.afterref)
        #args.beforeref = int(args.beforeref)
        #args.afterdate = str(args.afterdate)
        #args.beforedate = str(args.beforedate)
        #args.resultslabels = int(args.resultslabels)
        #args.sort = str(args.sort)

        if args.output_file != False:
            args.output_file = UnquoteString(args.output_file,quotes_map)
            args.output_file = Path(args.output_file).resolve()
            if args.output_file.exists() == False:
                args.output_file.parent.mkdir(exist_ok =True, parents = True)
                args.output_file.touch()
            print(f"Output file: {args.output_file}") if args.verbose else 0
        
        if args.extract_links != False:
            args.extract_links = UnquoteString(args.extract_links,quotes_map)
            args.extract_links = Path(args.extract_links).resolve()
            if args.extract_links.exists() == False:
                args.extract_links.parent.mkdir(exist_ok =True, parents = True)
                args.extract_links.touch()
            print(f"Links file: {args.extract_links}") if args.verbose else 0
        
        if args.download_links != False:
            args.download_links = UnquoteString(args.download_links,quotes_map)
            args.download_links = Path(args.download_links).resolve()
            if args.download_links.exists() == False:
                Path.mkdir(args.download_links,parents=True,exist_ok=True)
            print(f"Download directory: {args.download_links}") if args.verbose else 0
        
        #args.refresh_headers = bool(args.refresh_headers)
        #args.generate_results_files = bool(args.generate_results_files)
        #args.list_columns = bool(args.list_columns)
        #args.version = bool(args.version)
        #args.headers = bool(args.headers)
        #args.no_items = bool(args.no_items)
    return args

def ProcessTimezone(args):
    relative_time = dt.now()




    return relative_time
    pass

# Program
if __name__ == '__main__':
    

    #inputs - Abbrev - GMT, CET
    #       - offset - +05:00, -12:00

    print("getform.py started with the following arguments:")
    # Generate loop for asynchornous code execution
    loop = asyncio.get_event_loop()
    # Set up arguments from CLI input and some other initial vars
    statistics = Stats()
    arguments = SetupArgumentParser()[0]
    arguments = SanitizeArguments(arguments)
    

    # Checks for python version and program version
    CheckVersion(arguments.version,loop,arguments.verbose)

    # Generates initial variables from argparse arguments provided
    url_base=f"https://{arguments.server}.formsite.com/api/v2/{arguments.directory}"
    url_files=f"https://{arguments.server}.formsite.com/{arguments.directory}/files/"
    url_forms=f"{url_base}/forms/{arguments.form}/"

    # Generates headers for parametrs for API results request, used in function below
    authHeader = GenerateAuthHeader(arguments)
    resultsParams = GenerateResultsHeader(arguments)
    itemsParams = {"results_labels":arguments.resultslabels}
    print(f"results_labels: {arguments.resultslabels}") if arguments.verbose == True else 0

    # Asynchronous API calls
    future = asyncio.ensure_future(performAPIrequests(url_forms,authHeader,itemsParams,resultsParams,arguments,statistics))
    resultsContent_List,itemsContent = loop.run_until_complete(future)

    # This code will get executed if you provide the -l argument
    if arguments.list_columns is True:
        ListColumns(itemsContent)
        quit()
    
    # Load downloaded json files
    items_LoadedObject = LoadItemsAsJsonObject(itemsContent) 
    results_LoadedObject = LoadResultsAsJsonObject(resultsContent_List)

        # If there are no results in parameters specified, quit program.
    if len(results_LoadedObject[0]['results']) == 0:
        print("There are no results in specified parameters.")
        quit()
    
    # Create main dataframe with Results Responses Jsons
    HardCodedDF = CreateMainDataframe(results_LoadedObject)
    ItemsDF = pd.DataFrame(SeparatePaginatedItems(results_LoadedObject),columns=CreateItemsHeaders(items_LoadedObject))

    # Convert date formats from ISO 8601 TO MM/DD/YYYY hh:mm:ss and sets other formats that usually get generated when exporting
    HardCodedDF['date_update'] = HardCodedDF['date_update'].apply(lambda x: FixDates(x))
    HardCodedDF['date_start'] = HardCodedDF['date_start'].apply(lambda x: FixDates(x))
    HardCodedDF['date_finish'] = HardCodedDF['date_finish'].apply(lambda x: FixDates(x))
    HardCodedDF['duration'] = HardCodedDF['date_finish'] - HardCodedDF['date_start']
    HardCodedDF['duration'] = HardCodedDF['duration'].apply(lambda x: x.total_seconds())

    # Merges dataframes into a final structure
    df_1,df_2 = RenameHardcodedCols(HardCodedDF.reset_index(drop=True))
    FullDataframe = pd.concat([df_1, ItemsDF, df_2], axis=1)

    # Write EXCEL/JSON/CSV from constructed array
    WriteResults(arguments, FullDataframe, 'utf-8', ',', '\n', csv.QUOTE_ALL, "%Y-%m-%d--%H-%M-%S%z")
    
    # Special case of option -x or -D
    if arguments.extract_links != False or arguments.download_links != False:
        temp_df = FullDataframe
        temp_df.columns = [n for n in range(0,len(temp_df.columns))]
        links = []
        print("\nExtracting links from export...\n")
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
                x_filename = f"links_{arguments.form}_{dt.now().strftime('%Y-%m-%d--%H-%M-%S%z')}.txt"
            else:
                x_filename = arguments.extract_links
            WriteLinks(links,x_filename,arguments.verbose)
            print(f"Formsite download links extracted:    {x_filename}")
        if arguments.download_links != False:
            future = asyncio.ensure_future(FileDownloadLoop(links,url_files,arguments))
            loop.run_until_complete(future)
    # End
    print('API calls: %d' % statistics.num_pages)
    quit()