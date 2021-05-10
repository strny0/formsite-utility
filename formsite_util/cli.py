#!/usr/bin/env python3
"""
cli.py

CLI interface using argparse for formsite_util.core
"""
import csv
import sys
from time import perf_counter
import argparse
from formsite_util.core import FormsiteParams, FormsiteCredentials, FormsiteInterface, __version__

def gather_args() -> argparse.Namespace:
    """Gathers supported cli inputs."""
    parser = argparse.ArgumentParser(
        prog="formsite-util",
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
               "| 5xx  | Unexpected internal error.                  |\n\n"
               "formsite-util  Copyright (C) 2021  Jakub Strnad\n"
               "This program comes with ABSOLUTELY NO WARRANTY; for details see LICENSE.md\n"
               "This is free software, and you are welcome to redistribute it under certain conditions.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-V', '--version', action='version', version=f"%(prog)s {__version__}\n")
    g_auth = parser.add_argument_group('Authorization')
    g_params = parser.add_argument_group('Results Parameters')
    g_output = parser.add_argument_group('Output file')
    g_extract = parser.add_argument_group('Extract links')
    g_download = parser.add_argument_group('Download files')
    g_other = parser.add_argument_group('Other functions')
    g_debug = parser.add_argument_group('Debugging')
    g_nocreds = parser.add_mutually_exclusive_group(required=False)

    g_auth.add_argument('-t', '--token', type=str, default=None, required=True,
                        help="Your Formsite API token.")
    g_auth.add_argument('-s', '--server', type=str, default=None, required=True,
                        help="Your Formsite server. A part of the url. https://fsX.forms… <- the 'fsX' part."
                        "\nFor example 'fs22'.")
    g_auth.add_argument('-d', '--directory', type=str, default=None, required=True,
                        help="Your Formsite directory. Found under [Share > Links > Directory].")
    g_params.add_argument('-f', '--form', type=str, default=None,
                          help="Your Formsite form ID. Found under [Share > Links > Directory].")
    g_params.add_argument('--afterref', type=int, default=None,
                          help="Get results greater than a specified Reference #."
                          "\nMust be an integer.")
    g_params.add_argument('--beforeref', type=int, default=None,
                          help="Get results lesser than a specified Reference #."
                          "\nMust be an integer.")
    g_params.add_argument('--afterdate', type=str, default=None,
                          help="Get results after a specified date."
                          "\nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
                          "\nThis date is in your local timezone, unless specified otherwise.")
    g_params.add_argument('--beforedate', type=str, default=None,
                          help="Get results before a specified date."
                          "\nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
                          "\nThis date is in your local timezone, unless specified otherwise.")
    g_params.add_argument('--sort', choices=['asc', 'desc'], type=str, default="desc",
                          help="Determines how the output CSV will be sorted. Defaults to descending.")
    g_params.add_argument('--resultslabels', type=int, default=0,
                          help="Use specific results labels for your CSV headers."
                          "\nDefaults to 0 = first available set of results labels or default question labels.")
    g_params.add_argument('--resultsview', type=int, default=11,
                          help="Use specific results view for your CSV headers."
                          "\nDefaults to 11 = Items+Statistics. Other values currently not supported.")
    g_params.add_argument('-T', '--timezone', default='local',
                          help="Specify the timezone relative to which you want your results."
                          "\nBy default, results come relative to your local timezone."
                          "\nInput either name of the timezone from this list:"
                          "\nhttps://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
                          "\nYou can specify a manual offset in format +02:00 or -0200 from your LOCAL time"
                          "\n[Examples: database names] (avoid using deprecated ones)"
                          "\n'America/Chicago'"
                          "\n'Europe/Paris'"
                          "\n'America/New_York'"
                          "\n'Asia/Bangkok'")
    g_output.add_argument('-o', '--output_file', nargs='?', default=False, const='default',
                          help="Specify output file name and location."
                          "\nDefaults to export_yyyymmdd_formID.csv in the folder of the script."
                          "\nSupported output formats are (.csv|.xlsx|.pkl|.pickle|.json|.parquet|.md|.txt)")
    g_output.add_argument('--encoding', type=str, default='utf-8',
                          help="Specify encoding of the output file (if output format supports it)."
                          "\nDefaults to 'utf-8'")
    g_output.add_argument('--separator', type=str, default=',',
                          help="Specify separator of the output file (if output format supports it)."
                          "\nDefaults to ',' (comma)")
    g_output.add_argument('--line_terminator', type=str, choices={"LF", "CR", "CRLF"}, default="LF",
                          help="Specify line terminator of the output file (if output format supports it)"
                          "\nDefaults to '\\n' (LF) (line feed)")
    g_output.add_argument('--quoting', type=str, choices={"MINIMAL", "ALL", "NONNUMERIC", "NONE"}, default="MINIMAL",
                          help="Specify quoting level of the output file (if output format supports it)."
                          "\nDefaults to 'MINIMAL'"
                          "\nMore info about the quoting levels: https://docs.python.org/3/library/csv.html")
    g_output.add_argument('--date_format', default="%Y-%m-%d %H:%M:%S",
                          help="Specify datetime format in output file using python strftime directives."
                          "\nDefaults to '%%Y-%%m-%%d %%H:%%M:%%S' which is yyyy-mm-dd HH:MM:SS"
                          "\nYou can find the possible format directives here:"
                          "\nhttps://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior")
    g_extract.add_argument('-x', '--extract_links', nargs='?', default=False, const='default',
                           help="Outputs a .txt file with all formsite files urls in specified form."
                           "\nYou can specify file name or location, for example:"
                           "\n'-x C:\\Users\\MyUsername\\Desktop\\download_links.txt'."
                           "\nIf you don't specify a location, it will default to the folder of the script.")
    g_download.add_argument('-D', '--download_links', nargs='?', default=False, const='default',
                            help="If you include this flag, all formsite links in the export will be downloaded to a folder."
                            "\nYou can specify location, for example `-D 'C:\\Users\\My Username\\Desktop\\downloads'"
                            "\nIf you don't specify a location, it will default to the folder of the script.")
    g_other.add_argument('-S', '--store_latest_ref', nargs='?', default=False, const='default',
                         help="If you enable this option, a text file `latest_ref.txt` will be created."
                         "\nThis file will only contain the highest reference number in the export."
                         "\nIf there are no results in your export, nothing will happen.")
    g_extract.add_argument('-X', '--links_regex', type=str, default='.+',
                           help="Keep only links that match the regex you provide."
                           "\nWon't do anything if -x or -d arguments are not provided."
                           "\nDefaults to '.+'. Example usage: '-X \\.json$' would only give you files that have .json extension.")
    g_download.add_argument('-c', '--concurrent_downloads', default=10, type=int,
                            help="You can specify the number of concurrent download tasks."
                            "\nMore for large numbers of small files, less for large files."
                            "\nDefault is 10")
    g_download.add_argument('-n', '--dont_overwrite_downloads', default=True, action="store_false",
                            help="Checks if files already exist in download directory based on filename, if yes, doesn't re-download them.")
    g_download.add_argument('-R', '--filename_regex', default='', type=str,
                            help="If you include this argument, filenames of the files you download from formsite "
                            "\nservers will remove all characters from their name that dont match the regex."
                            "\nExpecting an input of allowed characters, for example: -R '[^\\w\\_\\-]+'"
                            "\nAny files that would be overwritten as a result of the removal of characters will be appended with _1, _2, etc.")
    g_download.add_argument('--timeout', nargs=1, default=80, type=int,
                            help="Timeout in seconds for each individual file download."
                            "\nIf download time exceeds it, it will throw a timeout error and retry up until retries. Defaults to 80.")
    g_download.add_argument('--retries', nargs=1, default=1, type=int,
                            help="Number of times to retry downloading files if the download fails. Defaults to 1.")
    g_download.add_argument('--get_download_status', default=False, action='store_true',
                            help="If you enable this option, a text file with status for each downloaded link will be saved.")
    g_download.add_argument('--stripprefix', default=False, action='store_true',
                            help="If you enable this option, filenames of downloaded files will not have f-xxx-xxx- prefix.")
    g_nocreds.add_argument('-l', '--list_columns', action="store_true", default=False,
                           help="Outputs a table of column ID - column name mappings."
                           "\nRequires login info and form id. Overrides all other functionality of the program.")
    g_nocreds.add_argument('-L', '--list_forms', nargs='?', default=False, const='default',
                           help="By itself, prints all forms, their form ids and status. You can specify a file to save the data into."
                           "\nExample: '-L ./list_of_forms.csv' to output to file or '-L' by itself to print to console."
                           "\nRequires login info. Overrides all other functionality of the program.")
    g_debug.add_argument('--sort_list_by', default='name', choices={'name', 'form_id', 'resultsCount', 'filesSize'},
                           help="You may chose what to sort -L commands by in descending order. Defaults to name.")
    g_debug.add_argument('--disable_progressbars', action="store_true", default=False,
                         help="If you use this flag, program will not display progressbars to console.")
    g_debug.add_argument('--generate_results_jsons', action="store_true", default=False,
                         help="If you use this flag, program will output raw results in json format from API requests."
                         "\nUseful for debugging purposes.")
    g_debug.add_argument('--generate_items_jsons', action="store_true", default=False,
                         help="If you use this flag, program will not store headers for later reuse.")
    g_debug.add_argument('-v', '--verbose', action="store_true", default=False,
                         help="If you use this flag, program will log progress in greater detail.")
    return parser.parse_known_args()[0]

def main():
    """formsite_util CLI entrypoint."""
    t_0 = perf_counter()
    arguments = gather_args()
    parameters = FormsiteParams(afterref=arguments.afterref,
                                beforeref=arguments.beforeref,
                                afterdate=arguments.afterdate,
                                beforedate=arguments.beforedate,
                                resultslabels=arguments.resultslabels,
                                resultsview=arguments.resultsview,
                                timezone=arguments.timezone,
                                sort=arguments.sort)

    authorization = FormsiteCredentials(arguments.token,
                                        arguments.server,
                                        arguments.directory)

    interface = FormsiteInterface(arguments.form,
                                  authorization,
                                  params=parameters,
                                  verbose=arguments.verbose,
                                  display_progress=not arguments.disable_progressbars)

    if arguments.list_forms is not False:
        if arguments.list_forms == 'default':
            interface.ListAllForms(display=True, sort_by=arguments.sort_list_by)
        else:
            interface.ListAllForms(save2csv=arguments.list_forms)
            print(f'saved list of forms to {arguments.list_forms}')
        return 0

    if arguments.list_columns is not False:
        interface.ListColumns()
        return 0

    if arguments.output_file is not False:
        if interface.Data is None:
            interface.FetchResults(save_results_jsons=arguments.generate_results_jsons,
                                   save_items_json=arguments.generate_items_jsons)
        line_term = {"LF":"\n", "CR":"\r", "CRLF":"\r\n"}
        if arguments.output_file == 'default':
            default_filename = f'./export_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}.csv'
        else:
            default_filename = arguments.output_file

        interface.WriteResults(default_filename,
                               date_format=arguments.date_format,
                               encoding=arguments.encoding,
                               separator=arguments.separator,
                               line_terminator=line_term.get(arguments.line_terminator),
                               quoting=eval(f"csv.QUOTE_{arguments.quoting}"))
        print("export complete")

    if arguments.extract_links is not False:
        if interface.Data is None:
            interface.FetchResults(save_results_jsons=arguments.generate_results_jsons,
                                   save_items_json=arguments.generate_items_jsons)
        if arguments.extract_links == 'default':
            default_filename = f'./links_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}.txt'
            interface.WriteLinks(
                default_filename, links_regex=arguments.links_regex)
        else:
            interface.WriteLinks(arguments.extract_links,
                                 links_regex=arguments.links_regex)
        print("links extracted")

    if arguments.download_links is not False:
        if interface.Data is None:
            interface.FetchResults(save_results_jsons=arguments.generate_results_jsons,
                                   save_items_json=arguments.generate_items_jsons)
        if arguments.download_links == 'default':
            default_folder = f'./download_{interface.form_id}_{interface.params.local_datetime.strftime("%Y-%m-%d--%H-%M-%S")}'
        else:
            default_folder = arguments.download_links

        interface.DownloadFiles(default_folder,
                                max_concurrent_downloads=arguments.concurrent_downloads,
                                links_regex=arguments.links_regex,
                                filename_regex=arguments.filename_regex,
                                overwrite_existing=arguments.dont_overwrite_downloads,
                                report_downloads=arguments.get_download_status,
                                timeout=arguments.timeout,
                                retries=arguments.retries,
                                strip_prefix=arguments.stripprefix)
        print("download complete")

    if arguments.store_latest_ref is not False:
        if interface.Data is None:
            interface.FetchResults(save_results_jsons=arguments.generate_results_jsons,
                                   save_items_json=arguments.generate_items_jsons)
        if arguments.store_latest_ref == 'default':
            default_filename = './latest_ref.txt'
        else:
            default_filename = arguments.store_latest_ref

        interface.WriteLatestRef(default_filename)
        print("latest reference saved")

    print(f'done in {(perf_counter() - t_0):0.2f} seconds!')
    return 0


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] > 5:
        sys.exit(main())
    else:
        raise Exception("Unsupported python version.")
