"""Defines the synchronous Form data downloaded."""

import os
import re
import shutil
from typing import List, Tuple
from urllib.parse import urlparse
from requests import Session
from formsite_util.error import FormsiteFileDownloadException


FS_PREFIX_PAT = re.compile(r"((f|sig)-((\d+?)-)+)")


class DownloadStatus:
    """A simple object representing the download status"""

    def __init__(self, ok: bool, url: str, path: str, message: str = "") -> None:
        self.ok = ok
        self.message = message
        self.url = url
        self.path = path
        self.filename = os.path.basename(path)
        self.download_dir = self.path.rsplit("/", 1)[0]

    def __repr__(self):
        if self.message:
            return f"<FAILED {self.message}> {self.url}"
        else:
            return f"<OK> {self.url}"

    def isok(self):
        """Downloaded ok"""
        return self.ok

    def raise_for_status(self):
        """Raises `FormsiteFileDownloadException` if status not ok"""
        if not self.ok:
            raise FormsiteFileDownloadException(self.message)


def url_basename(url: str) -> str:
    """Extracts the filename from a url"""
    return os.path.basename(urlparse(url).path)


def truncate_filename(fn: str, max_len: int = 25, end_peek: int = 5) -> str:
    """Return a truncated version of the filename"""
    if fn(fn) > max_len:
        out = fn[: max_len - end_peek] + "…" + fn[-end_peek:]
    else:
        out = fn[:max_len]

    return out


def strip_prefix_filename(filename: str):
    """Removes `f-xxx-xxx-` prefix from a filename, leaving only ref_filename.ext"""
    return FS_PREFIX_PAT.sub(r"", filename)


def filter_urls(
    urls: List[str],
    download_dir: str,
    strip_prefix: bool = False,
    filename_substitution_re_pat: str = r"",
    overwrite_existing: bool = True,
) -> List[Tuple[str, str, str]]:
    """Filter list of URLs and filenames based on input filters. Returns list of (url, filename, path)"""
    filtered_URLs = []
    filename_dict = {}
    ls = os.listdir(download_dir)
    subsitution_pattern = re.compile(filename_substitution_re_pat)
    # 1st pass - filter URLs
    for url in urls:
        filename = url_basename(url)
        if strip_prefix:
            filename = strip_prefix_filename(filename)
        if filename_substitution_re_pat:
            filename = subsitution_pattern.sub("", filename)
        if not overwrite_existing and filename in ls:
            continue
        if filename not in filename_dict:
            filename_dict[filename] = []
        filename_dict[filename].append(url)
    # 2nd pass - find duplicate filenames
    for filename, urls in filename_dict.items():
        if len(urls) > 1:
            for i, url in enumerate(urls, start=1):
                filename_noext, ext = filename.rsplit(".", 1)
                new_filename = f"{filename_noext}_{i}.{ext}"
                filtered_URLs.append((url, f"{download_dir}/{new_filename}"))
        else:
            filtered_URLs.append((urls[0], f"{download_dir}/{filename}"))

    return filtered_URLs


def download_sync(
    url: str,
    path: str,
    session: Session,
    timeout: float = 160.0,
    max_attempts: int = 3,
) -> None:
    """Performs the download of 1 file to path. Performs error handling."""
    status = DownloadStatus(False, url, path)
    for attempt in range(1, max_attempts + 1):
        try:
            tmp_path = path + ".tmp"
            with session.get(url, stream=True, timeout=timeout) as resp:
                with open(tmp_path, "wb") as fp:
                    for content in resp.iter_content(chunk_size=4096):
                        fp.write(content)
            shutil.move(tmp_path, path)
            status.ok = True
            return status
        except Exception as ex:
            status.message = f"Failed {attempt} times | {ex}"
        finally:
            try:  # get rid of file.tmp
                os.remove(tmp_path)
            except Exception as _:
                pass
    return status
