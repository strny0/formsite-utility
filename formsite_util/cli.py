#!/usr/bin/env python3
import argparse
from formsite_util.core import FormsiteParams, FormsiteCredentials, FormsiteInterface
from time import perf_counter


def GatherArguments():
    parser = argparse.ArgumentParser(
        description="Github of author: https://github.com/strny0/formsite-utility\n"
                    "This program performs an export of a specified formsite form with parameters.\n"
                    "A faster alternative to a manual export from the formsite website, that can be used for workflow automation.\n"
                    "Allows for the extraction of assets saved on formsite servers.",
        epilog="More info can be found at Formsite API v2 help page:    \n"
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
    parser.add_argument('-V', '--version', action='version', version="1.2.7.6")
    g_login = parser.add_argument_group('Login')
    g_params = parser.add_argument_group('Results Parameters')
    g_functions = parser.add_argument_group('Functions')
    g_func_params = parser.add_argument_group('Functions Parameters')
    g_debug = parser.add_argument_group('Debugging')
    g_nocreds = parser.add_mutually_exclusive_group(required=False)

    g_login.add_argument('-t', '--token', type=str, default=None, required=True,
                         help="Your Formsite API token. Required."
                         )
    g_login.add_argument('-s', '--server', type=str, default=None, required=True,
                         help="Your Formsite server. A part of the url. https://fsX.forms… <- the 'fsX' part. For example 'fs22'. Required."
                         )
    g_login.add_argument('-d', '--directory', type=str, default=None, required=True,
                         help="Your Formsite directory. Can be found under [Share > Links > Directory]. Required."
                         )
    g_params.add_argument('-f', '--form', type=str, default=None,
                          help="Your Formsite form ID. Can be found under [Share > Links > Directory]. Mostly required."
                          )
    g_params.add_argument('--afterref', type=int, default=0,
                          help="Get results greater than a specified Reference #. \nMust be an integer."
                          )
    g_params.add_argument('--beforeref', type=int, default=0,
                          help="Get results lesser than a specified Reference #. \nMust be an integer."
                          )
    g_params.add_argument('--afterdate', type=str, default="",
                          help="Get results after a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
                          "\nThis date is in your local timezone, unless specified otherwise."
                          )
    g_params.add_argument('--beforedate', type=str, default="",
                          help="Get results before a specified date. \nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
                          "\nThis date is in your local timezone, unless specified otherwise."
                          )
    g_params.add_argument('--sort', choices=['asc', 'desc'], type=str,  default="desc",
                          help="Determines how the output CSV will be sorted. Defaults to descending."
                          )
    g_params.add_argument('--resultslabels', type=int, default=0,
                          help="Use specific results labels for your CSV headers."
                          "\nDefaults to 0, which takes the first set results labels or if those are not available, default question labels."
                          )
    g_params.add_argument('--resultsview', type=int, default=11,
                          help="Use specific results view for your CSV headers. Defaults to 11 = Items+Statistics. Other values currently not supported"
                          )
    g_params.add_argument('-F', '--date_format',  default="%Y-%m-%d %H:%M:%S",
                          help="Specify a quoted string using python datetime directives to specify what format you want your dates in (column: Date)."
                          "\nDefaults to '%%Y-%%m-%%d %%H:%%M:%%S' which is yyyy-mm-dd HH:MM:SS"
                          "\nYou can find the possible format directives here: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior"
                          )
    g_params.add_argument('-T', '--timezone',  default='local',
                          help="You can use this flag to specify the timezone relative to which you want your results."
                          "\nThis is useful for when your organization is using a single formsite timezone for all subusers"
                          "\nInput either name of the timezone from this list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
                          "\nThe timezone database method accounts for daylight savings time."
                          "\nor an offset in the format +02:00 or +0200 or 0200 for a 2 hour later time (for example) from your LOCAL time"
                          "\n[Examples: offsets]"
                          "\n Offset    Cities (this does not account for daylight savings time)"
                          "\n'-08:00' - Los Angeles, Vancouver, Tijuana"
                          "\n'-07:00' - Denver, Edmonton, Ciudad Juarez"
                          "\n'-06:00' - Mexico City, Chicago, San Salvador"
                          "\n'-05:00' - New York, Toronto, Havana, Lima"
                          "\n'-03:00' - São Paulo, Buenos Aires, Montevideo"
                          "\n'+00:00' - London, Lisbon, Dakar"
                          "\n'+01:00' - Berlin, Rome, Paris, Prague"
                          "\n'+02:00' - Cairo, Kiev, Jerusalem, Athens, Sofia"
                          "\n'+03:00' - Moscow, Istanbul, Baghdad, Addis Ababa"
                          "\n'+04:00' - Dubai, Tbilisi, Yerevan"
                          "\n'+06:00' - Dhaka, Almaty, Omsk"
                          "\n'+07:00' - Jakarta, Ho Chi Minh City, Bangkok, Krasnoyarsk"
                          "\n'+08:00' - China - Shanghai, Taipei, Kuala Lumpur, Singapore, Perth, Manila, Makassar, Irkutsk"
                          "\n'+09:00' - Tokyo, Seoul, Pyongyang, Ambon, Chita"
                          "\n'+10:00' - Sydney, Port Moresby, Vladivostok"
                          "\n"
                          "\n[Examples: database names] avoid using deprecated ones"
                          "\n'America/Chicago'"
                          "\n'Europe/Paris'"
                          "\n'America/New_York'"
                          "\n'Asia/Bangkok'"
                          )
    g_functions.add_argument('-o', '--output_file', nargs='?', default=False, const='default',
                             help="Specify output file name and location. \nDefaults to export_yyyymmdd_formid.csv in the folder of the script."
                             )
    g_functions.add_argument('-x', '--extract_links', nargs='?',  default=False, const='default',
                             help="If you include this flag, you will get a text file that has all links that start with formsite url stored. \nYou can specify file name or location, for example '-x C:\\Users\\MyUsername\\Desktop\\download_links.txt'. \nIf you don't specify a location, it will default to the folder of the script."
                             )
    g_functions.add_argument('-D', '--download_links', nargs='?',  default=False, const='default',
                             help="If you include this flag, all formsite links in the export will be downloaded to a folder."
                             "\nYou can specify location, for example `-D 'C:\\Users\\My Username\\Desktop\\downloads'"
                             "\nIf you don't specify a location, it will default to the folder of the script."
                             )
    g_func_params.add_argument('-X', '--links_regex', type=str,  default='.+',
                               help="Keep only links that match the regex you provide."
                               "\nWon't do anything if -x or -d arguments are not provided."
                               "\nDefaults to '.+'. Example usage: '-X \\.json$' would only give you files that have .json extension."
                               )
    g_func_params.add_argument('-c', '--concurrent_downloads',  default=10, type=int,
                               help="You can specify the number of concurrent download tasks."
                               "\nMore for large numbers of small files, less for large files."
                               "\nDefault is 10")
    g_func_params.add_argument('-n', '--dont_overwrite_downloads',  default=True, action="store_false",
                               help="If you include this flag, files with the same filenames as you are downloading will not be overwritten and re-downloaded.")
    g_func_params.add_argument('-R', '--filename_regex',  default='', type=str,
                               help="If you include this argument, filenames of the files you download from formsite servers will remove all characters from their name that dont match the regex you provide."
                               "\nExpecting an input of allowed characters, for example: -R '[^A-Za-z0-9\\_\\-]+'"
                               "\nAny files that would be overwritten as a result of the removal of characters will be appended with _1, _2, etc.")
    g_functions.add_argument('-S', '--store_latest_ref',  nargs='?',  default=False, const='default',
                             help="If you enable this option, a text file `latest_ref.txt` will be created. \nThis file will only contain the highest reference number in the export. \nIf there are no results in your export, nothign will happen.")
    g_func_params.add_argument('--timeout',  nargs=1,  default=80, type=int,
                             help="Timeout in seconds for each individual file download. If download time exceeds it, it will throw a timeout error and retry up until retries. Defaults to 80.")
    g_func_params.add_argument('--retries',  nargs=1,  default=1, type=int,
                             help="Number of times to retry downloading files if the download fails. Defaults to 1.")
    g_func_params.add_argument('--get_download_status', default=False, action='store_true',
                             help="If you enable this option, a text file with status for each downloaded link will be saved (complete or incomplete).")
    g_nocreds.add_argument('-l', '--list_columns', action="store_true",  default=False,
                           help="If you use this flag, program will output mapping of what column belongs to which column ID instead of actually running, useful for figuring out search arguments."
                           "\nRequires login info and form id. Overrides all other functionality of the program."
                           )
    g_nocreds.add_argument('-L', '--list_forms', nargs='?',  default=False, const='default',
                           help="By itself, prints all forms, their form ids and status. You can specify a file to save the data into."
                           "\nExample: '-L ./list_of_forms.csv' to output to file or '-L' by itself to print to console."
                           "\nRequires login info. Overrides all other functionality of the program."
                           )
    g_debug.add_argument('--generate_results_jsons', action="store_true",  default=False,
                         help="If you use this flag, program will output raw results in json format from API requests."
                         "\nUseful for debugging purposes."
                         )
    g_debug.add_argument('--generate_items_jsons', action="store_true",  default=False,
                         help="If you use this flag, program will not store headers for later reuse."
                         )
    g_debug.add_argument('--refresh_headers', action="store_true",  default=False,
                         help="If you include this flag, items_formid.json will be re-downloaded with latest headers if they already exist."
                         )
    g_debug.add_argument('-v', '--verbose', action="store_true",  default=False,
                         help="If you use this flag, program will log progress in greater detail."
                         )
    return parser.parse_known_args()[0]


def main():
    t0 = perf_counter()
    arguments = GatherArguments()
    parameters = FormsiteParams(
        afterref=arguments.afterref,
        beforeref=arguments.beforeref,
        afterdate=arguments.afterdate,
        beforedate=arguments.beforedate,
        resultslabels=arguments.resultslabels,
        resultsview=arguments.resultsview,
        timezone=arguments.timezone,
        date_format=arguments.date_format,
        sort=arguments.sort)
    credentials = FormsiteCredentials(arguments.token, arguments.server, arguments.directory)

    with FormsiteInterface(arguments.form, credentials, params=parameters, verbose=arguments.verbose) as interface:
        if arguments.list_forms is not False:
            if arguments.list_forms == 'default':
                interface.ListAllForms(display2console=True)
            else:
                interface.ListAllForms(display2console=True,
                                       save2csv=arguments.list_forms)
            return 0
        if arguments.list_columns is not False:
            interface.ListColumns()
            return 0

        if arguments.output_file is not False:
            interface.FetchResults(save_results_jsons=arguments.generate_results_jsons,
                                   save_items_json=arguments.generate_items_jsons, refresh_items_json=arguments.refresh_headers)
            if arguments.output_file == 'default':
                default_filename = f'./export_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}.csv'
                interface.WriteResults(
                    default_filename, date_format=arguments.date_format)
            else:
                interface.WriteResults(arguments.output_file,
                                       date_format=arguments.date_format)
            print("export complete")
        if arguments.extract_links is not False:
            if arguments.extract_links == 'default':
                default_filename = f'./links_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}.txt'
                interface.WriteLinks(
                    default_filename, links_regex=arguments.links_regex)
            else:
                interface.WriteLinks(arguments.extract_links,
                                     links_regex=arguments.links_regex)
            print("links extracted")
        if arguments.download_links is not False:
            if arguments.download_links == 'default':
                default_folder = f'./download_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}'
                interface.DownloadFiles(
                    default_folder, max_concurrent_downloads=arguments.concurrent_downloads, links_regex=arguments.links_regex, filename_regex=arguments.filename_regex, overwrite_existing=arguments.dont_overwrite_downloads)
            else:
                interface.DownloadFiles(
                    arguments.download_links, max_concurrent_downloads=arguments.concurrent_downloads, links_regex=arguments.links_regex, filename_regex=arguments.filename_regex, overwrite_existing=arguments.dont_overwrite_downloads, report_downloads=arguments.get_download_status, timeout=arguments.timeout, retries=arguments.retries)
            print("download complete")
        if arguments.store_latest_ref is not False:
            if arguments.store_latest_ref == 'default':
                default_filename = './latest_ref.txt'
                interface.WriteLatestRef(default_filename)
            else:
                interface.WriteLatestRef(arguments.store_latest_ref)
            print("latest reference saved")

        print(f'done in {(perf_counter() - t0):0.2f} seconds!')
        return 0


if __name__ == '__main__':
    exit(main())
