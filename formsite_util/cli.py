"""Defines the CLI tool and its logic"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime as dt
from argparse import ArgumentParser, RawTextHelpFormatter, Namespace
from tqdm.auto import tqdm
import pandas as pd

# ----
from formsite_util.form import FormsiteForm
from formsite_util.list import FormsiteFormsList
from formsite_util.parameters import FormsiteParameters
from formsite_util.logger import FormsiteLogger
from formsite_util.consts import QUOTE, LINE_TERM, TIMESTAMP
from formsite_util.__init__ import __version__

_FETCH_PBAR = None
_DOWNLOAD_PBAR = None


def main():
    """The main program (CLI)"""
    global _FETCH_PBAR
    global _DOWNLOAD_PBAR
    log = FormsiteLogger()
    args = get_args()

    # Initialize logging
    if args.verbose:
        sh = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("[%(levelname)s] %(message)s")
        sh.setFormatter(fmt)
        sh.setLevel(logging.DEBUG)
        log.addHandler(sh)
        args.disable_progressbars = True

    # Initialize session
    # ----
    if args.list_forms is not None:
        forms_list = FormsiteFormsList(args.token, args.server, args.directory)
        forms_list.fetch()
        # ----
        if not args.list_forms:
            if args.sort_list_by in ["results_count", "files_size"]:
                df = forms_list.data.sort_values(
                    by=args.sort_list_by,
                    ascending=False,
                )
            else:
                df = forms_list.data.sort_values(
                    by=args.sort_list_by,
                    ascending=True,
                )
            # ----
            df = df[["name", "form_id", "state", "results_count", "files_size_human"]]
            df.columns = ["name", "form_id", "state", "results count", "files size"]
            pd.set_option("display.max_rows", None)
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", None)
            pd.set_option("display.max_colwidth", 42)
            print(df.reset_index(drop=True))
        else:
            path = Path(args.list_forms).resolve().as_posix()
            forms_list.to_csv(path)
        sys.exit(0)
    # ----
    form = FormsiteForm(args.form, args.token, args.server, args.directory)
    params = FormsiteParameters(
        last=args.last,
        after_id=args.afterref,
        before_id=args.beforeref,
        after_date=args.afterdate,
        before_date=args.beforedate,
        resultsview=args.resultsview,
        timezone=args.timezone,
        sort=args.sort,
    )
    if not args.disable_progressbars:
        _FETCH_PBAR = tqdm(desc=f"Exporting {args.form}")
    form.fetch(
        params=params,
        fetch_callback=fetch_pbar_callback,
    )
    if not args.disable_progressbars:
        _FETCH_PBAR.close()
    # ----
    if args.output is not None:
        save_output(args, form)
    if args.latest_id is not None:
        save_latest_id(args, form)
    if args.extract is not None:
        save_extract(args, form)
    if args.download is not None:
        loop = asyncio.get_event_loop()
        if not args.disable_progressbars:
            _DOWNLOAD_PBAR = tqdm(desc=f"Downloading from {args.form}")
        save_download(args, form, loop)
        if not args.disable_progressbars:
            _DOWNLOAD_PBAR.close()
    # ----


def save_output(args: Namespace, form: FormsiteForm):
    """Save file based on extension."""
    # Supported (.csv|.xlsx|.pickle|.parquet|.feather|.hdf)
    if not args.output:
        path = Path(f"./export_{form.form_id}_{TIMESTAMP}.csv").resolve()
    else:
        path = Path(args.output).resolve()
    os.makedirs(path.parent.as_posix(), exist_ok=True)
    str_path = path.as_posix()
    ext = str_path.rsplit(".", 1)[-1].lower()
    df = form.data_labels if args.use_items else form.data
    if ext == "xlsx":
        # Write to excel with reasonable default settings
        df.to_excel(str_path, encoding="utf-8", index=False)
    elif ext in ("pickle", "pkl"):
        df.to_pickle(str_path)
    elif ext == "parquet":
        df.to_parquet(str_path)
    elif ext == "feather":
        df.to_feather(str_path)
    elif ext == "hdf":
        df.to_hdf(str_path, key=form.form_id)
    # Default to CSV
    else:
        df.to_csv(
            str_path,
            encoding=args.encoding,
            index=False,
            date_format=args.date_format,
            line_terminator=LINE_TERM.get(
                args.line_terminator, LINE_TERM.get("os_default")
            ),
            quoting=QUOTE[args.quoting],
            sep=args.separator,
        )


def save_latest_id(args: Namespace, form: FormsiteForm):
    """Write latest Reference # to a file (if it exists)"""
    m = None
    if form.uses_items is False and "id" in form.data.columns:
        m = max(form.data["id"])
    elif form.uses_items is True and "Reference #" in form.data.columns:
        m = max(form.data["Reference #"])

    if m is not None:
        with open(args.latest_id, "w", encoding="utf-8") as fp:
            fp.write(f"{m}\n")


def save_extract(args: Namespace, form: FormsiteForm):
    """Extract all URLs from the FileUpload controls and save them to a file"""

    if not args.extract:
        path = Path(f"./url_{form.form_id}_{TIMESTAMP}.txt").resolve()
    else:
        path = Path(args.extract).resolve()
    os.makedirs(path.parent.as_posix(), exist_ok=True)
    str_path = path.as_posix()
    URLs = form.extract_urls(args.extract_regex)
    with open(str_path, "w", encoding="utf-8") as fp:
        for url in URLs:
            fp.write(f"{url}\n")


def save_download(args: Namespace, form: FormsiteForm, loop: asyncio.AbstractEventLoop):
    """Download all files uploaded to the form using the File Upload control"""

    if not args.download:
        path = Path(f"./download_{form.form_id}_{TIMESTAMP}").resolve()
    else:
        path = Path(args.download).resolve()
    # ----
    os.makedirs(path.parent.as_posix(), exist_ok=True)
    str_path = path.as_posix()
    download = form.async_downloader(
        str_path,
        max_concurrent=args.concurrent_downloads,
        timeout=args.timeout,
        max_attempts=args.retries,
        url_filter_re=args.extract_regex,
        filename_substitution_re_pat=args.download_regex,
        overwrite_existing=args.dont_overwrite_downloads,
        strip_prefix=args.strip_prefix,
        callback=download_pbar_callback,
    )
    # ----
    loop.run_until_complete(download.run())


def fetch_pbar_callback(page: int, total_pages: int, data: dict) -> None:
    """Updates fetch progress bar (if enabled)"""
    if _FETCH_PBAR is None:
        return
    _FETCH_PBAR.total = total_pages
    _FETCH_PBAR.update(1)


def download_pbar_callback(url: str, filepath: str, total_files: int) -> None:
    """Updates download progress bar (if enabled)"""
    if _DOWNLOAD_PBAR is None:
        return
    _DOWNLOAD_PBAR.total = total_files
    _DOWNLOAD_PBAR.update(1)


def get_args() -> Namespace:
    """Uses argparse module to retrive argv arguments"""
    parser = ArgumentParser(
        prog="formsite-util",
        description="Github of author:\n"
        "https://github.com/strny0/formsite-utility\n"
        "This program performs an export of a specified formsite form with provided\nparameters.\n"
        "A faster alternative to a manual export from the formsite website, that can\nbe used for workflow automation.\n"
        "Allows download of files uploaded to the form.",
        epilog="More info can be found at Formsite API v2 help page:\n"
        "https://support.formsite.com/hc/en-us/articles/360000288594-API\n"
        "You can find API related information of a specific form under:"
        "[Form Settings > Integrations > Formsite API]\n"
        f"formsite-util  Copyright (C) {dt.now().year} Jakub Strnad\n"
        "This program comes with ABSOLUTELY NO WARRANTY; for details see LICENSE.md\n"
        "This is free software, and you are welcome to redistribute it.",
        formatter_class=RawTextHelpFormatter,
    )

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}\n",
    )
    g_auth = parser.add_argument_group("Authorization")
    g_params_r = parser.add_argument_group("Results Parameters")
    g_params_i = parser.add_argument_group("Items Parameters")
    g_output = parser.add_argument_group("Output file")
    g_extract = parser.add_argument_group("Extract links")
    g_download = parser.add_argument_group("Download files")
    g_other = parser.add_argument_group("Other functions")
    g_debug = parser.add_argument_group("Debugging")
    g_metadata = parser.add_mutually_exclusive_group(required=False)

    g_auth.add_argument(
        "-t",
        "--token",
        type=str,
        default=None,
        required=True,
        help="Your Formsite API token.",
    )
    g_auth.add_argument(
        "-s",
        "--server",
        type=str,
        default=None,
        metavar="FORMSITE_SERVER",
        required=True,
        help="Your Formsite server. A part of the url. https://fsX.forms… <- the 'fsX' part."
        "\nFor example 'fs22'.",
    )
    g_auth.add_argument(
        "-d",
        "--directory",
        type=str,
        default=None,
        metavar="FORMSITE_DIRECTORY",
        required=True,
        help="Your Formsite directory. Found under [Share > Links > Directory].",
    )
    g_params_r.add_argument(
        "-f",
        "--form",
        type=str,
        default=None,
        metavar="FORM_ID",
        help="Your Formsite form ID. Found under [Share > Links > Directory].",
    )
    g_params_r.add_argument(
        "--last",
        type=int,
        default=None,
        metavar="NUMBER",
        help="Gets last x results.",
    )
    g_params_r.add_argument(
        "-aID",
        "--afterref",
        type=int,
        default=None,
        metavar="NUMBER",
        help="Get results greater than a specified Reference #.",
    )
    g_params_r.add_argument(
        "-bID",
        "--beforeref",
        type=int,
        default=None,
        metavar="NUMBER",
        help="Get results lesser than a specified Reference #.",
    )
    g_params_r.add_argument(
        "-aDate",
        "--afterdate",
        type=str,
        default=None,
        metavar="DATETIME_STRING",
        help="Get results after a specified date."
        "\nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
        "\nThis date is in your local timezone, unless specified otherwise.",
    )
    g_params_r.add_argument(
        "-bDate",
        "--beforedate",
        type=str,
        default=None,
        metavar="DATETIME_STRING",
        help="Get results before a specified date."
        "\nMust be formatted as ISO 8601 UTC, YYYY-MM-DD, or YYYY-MM-DD HH:MM:SS."
        "\nThis date is in your local timezone, unless specified otherwise.",
    )
    g_params_r.add_argument(
        "--sort",
        choices=["asc", "desc"],
        type=str,
        default="desc",
        help="Determines how the output CSV will be sorted. Defaults to descending.",
    )
    g_params_i.add_argument(
        "--resultslabels",
        type=int,
        default=None,
        metavar="NUMBER",
        help="Use specific results labels for your CSV headers.\n"
        "Defaults to default Question labels.",
    )
    g_params_r.add_argument(
        "--resultsview",
        type=int,
        default=None,
        metavar="NUMBER",
        help="Extract a subset of columns with a resultsview ID. Defaults to 11 (All items + Metadata).",
    )
    g_params_r.add_argument(
        "-T",
        "--timezone",
        default="Etc/UTC",
        help="Specify the timezone relative to which you want your results.\n"
        "By default, results come in UTC.\n"
        "Input name of the timezone from this list:\n"
        "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones\n"
        "[Examples:]\n"
        "'America/Chicago'\n"
        "'Europe/Paris'\n"
        "'America/New_York'\n"
        "'Asia/Bangkok'",
    )
    g_params_r.add_argument(
        "--delay",
        type=int,
        metavar="NUMBER",
        default=3,
        help="Delay in seconds between each API call. Defaults to 3 seconds.",
    )
    g_output.add_argument(
        "-o",
        "--output",
        nargs="?",
        default=None,
        metavar="PATH/TO/FILE",
        const="",
        help="Specify output file name and location.\n"
        "Defaults to export_yyyymmdd_formID.csv in the folder of the script.\n"
        "Supported output formats are (.csv|.xlsx|.pickle|.parquet|.feather|.hdf)",
    )
    g_output.add_argument(
        "-i",
        "--use_items",
        action="store_false",
        default=True,
        help="Instead of regular headers uses default metadata and items ids",
    )
    g_output.add_argument(
        "--encoding",
        type=str,
        default="utf-8-sig",
        help="Specify encoding of the output file (if output format supports it).\n"
        "More info on possible values here:\n"
        "https://docs.python.org/3/library/codecs.html#standard-encodings\n"
        "Defaults to 'utf-8-sig', UTF-8 with BOM.",
    )
    g_output.add_argument(
        "--separator",
        type=str,
        default=",",
        help="Specify separator of the output file (if output format supports it).\n"
        "Defaults to ',' (comma)",
    )
    g_output.add_argument(
        "--line_terminator",
        type=str,
        choices={"LF", "CR", "CRLF", "os_default"},
        default="os_default",
        help="Specify line terminator of the output file (if output format supports it)\n"
        "Defaults to 'LF'.",
    )
    g_output.add_argument(
        "--quoting",
        type=str,
        choices={"QUOTE_MINIMAL", "QUOTE_ALL", "QUOTE_NONNUMERIC", "QUOTE_NONE"},
        default="QUOTE_MINIMAL",
        help="Specify quoting level of the output file (if output format supports it).\n"
        "Defaults to 'QUOTE_MINIMAL'\n"
        "More info about the quoting levels: https://docs.python.org/3/library/csv.html\n",
    )
    g_output.add_argument(
        "--date_format",
        default="%Y-%m-%d %H:%M:%S",
        metavar="'POSIX DATETIME DIRECTIVE'",
        help="Specify datetime format in output file using python strftime directives.\n"
        "Defaults to '%%Y-%%m-%%d %%H:%%M:%%S' which is yyyy-mm-dd HH:MM:SS\n"
        "You can find the possible format directives here:\n"
        "https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior",
    )
    g_extract.add_argument(
        "-x",
        "--extract",
        nargs="?",
        default=None,
        metavar="PATH/TO/FILE",
        const="",
        help="Outputs a .txt file with all formsite files urls in specified form."
        "\nYou can specify file name or location, for example:"
        "\n'-x C:\\Users\\MyUsername\\Desktop\\download_links.txt'."
        "\nIf you don't specify a location, it will default to the folder of the script.",
    )
    g_download.add_argument(
        "-D",
        "--download",
        nargs="?",
        default=None,
        metavar="PATH/TO/FILE",
        const="",
        help="If you include this flag, all formsite links in the export will be downloaded to a folder."
        "\nYou can specify location, for example `-D 'C:\\Users\\My Username\\Desktop\\downloads'"
        "\nIf you don't specify a location, it will default to the folder of the script.",
    )
    g_other.add_argument(
        "-S",
        "--latest_id",
        nargs="?",
        metavar="PATH/TO/FILE",
        default=None,
        const="",
        help="If you enable this option, a text file `latest_ref.txt` will be created."
        "\nThis file will only contain the highest reference number in the export."
        "\nIf there are no results in your export, nothing will happen."
        "\nYou may also specify an output file, `-S output_file.txt",
    )
    g_extract.add_argument(
        "-xre",
        "--extract_regex",
        type=str,
        metavar="'REGEX'",
        default=r".+",
        help="Keep only links that match the regex you provide."
        "\nWon't do anything if -x or -d arguments are not provided."
        "\nDefaults to '.+'. Example usage: '-X \\.json$' would only give you files that have .json extension.",
    )
    g_download.add_argument(
        "-c",
        "--concurrent_downloads",
        default=5,
        metavar="NUMBER",
        type=int,
        help="You can specify the number of concurrent download tasks."
        "\nMore for large numbers of small files, less for large files."
        "\nDefault is 5.",
    )
    g_download.add_argument(
        "-n",
        "--dont_overwrite_downloads",
        default=True,
        action="store_false",
        help="Checks if files already exist in download directory based on filename."
        "If they already exist, they are not re-downloaded.",
    )
    g_download.add_argument(
        "-Dre",
        "--download_regex",
        default=r"",
        metavar=R"'REGEX'",
        type=str,
        help="If you include this argument, filenames of the files you download from formsite "
        "\nservers will remove all characters from their name that dont match the regex."
        "\nExpecting an input of allowed characters, for example: -R '[^\\w\\_\\-]+'"
        "\nAny files that would be overwritten as a result of the removal of characters will be appended with _1, _2, etc.",
    )
    g_download.add_argument(
        "--timeout",
        nargs=1,
        default=80,
        type=int,
        help="Timeout in seconds for each individual file download."
        "\nIf download time exceeds it, it will throw a timeout error and retry up until retries. Defaults to 80.",
    )
    g_download.add_argument(
        "--retries",
        nargs=1,
        default=3,
        type=int,
        help="Number of times to retry downloading files if the download fails. Defaults to 1.",
    )
    g_download.add_argument(
        "--strip_prefix",
        default=False,
        action="store_true",
        help="If you enable this option, filenames of downloaded files will not have f-xxx-xxx- prefix.",
    )

    g_metadata.add_argument(
        "-l",
        "--list_forms",
        nargs="?",
        default=None,
        const="",
        help="By itself, prints all forms, their form ids and status. You can specify a file to save the data into.\n"
        "Example: '-L ./list_of_forms.csv' to output to file or '-L' by itself to print to console.\n"
        "Requires login info. Overrides all other functionality of the program.",
    )
    g_other.add_argument(
        "-Q",
        "--sort_list_by",
        default="name",
        choices={"name", "results_count", "files_size"},
        help="You may chose what to sort -l commands by in descending order. Defaults to name.",
    )
    g_other.add_argument(
        "-P",
        "--disable_progressbars",
        action="store_true",
        default=False,
        help="If you use this flag, program will not display progressbars to console.",
    )

    g_debug.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="Enable verbose logging to a log file.",
    )

    args, uargs = parser.parse_known_args()

    if uargs:  # if any unknown arguments were passed
        print(f"Unknown arguments: {uargs}")
        sys.exit(1)

    return args


if __name__ == "__main__":
    main()
