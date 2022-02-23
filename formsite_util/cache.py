"""

cache.py

"""

from collections import defaultdict
import os
from pathlib import Path
from typing import Tuple, Union
import json
import pandas as pd

# ----
from formsite_util.form_error import FormsiteUncachableParametersException
from formsite_util.form import FormsiteForm
from formsite_util.form_data import FormData
from formsite_util.logger import FormsiteLogger


class FormCache:
    """Store and perpetually update data in a particular location"""

    def __init__(
        self,
        cache_dir: str,
        serialization_format: str = "feather",
    ) -> None:
        """FormCache constructor

        Args:
            cache_dir (str): Path where you want to store the form.
            serialization_format (str, optional): Defaults to "feather".

        Serialization formts:
             `feather`
             `hdf`
             `parquet`
             `pickle`
             `json`
             `csv`
        """
        _VALID_FORMATS = ["feather", "hdf", "parquet", "pickle", "json", "csv"]

        assert (
            serialization_format in _VALID_FORMATS
        ), f"Invalid serialization format: {serialization_format}"
        self.logger: FormsiteLogger = FormsiteLogger()
        self.cache_dir = Path(cache_dir).resolve().as_posix()
        self.s_format = serialization_format
        os.makedirs(self.cache_dir, exist_ok=True)

    def save(self, form: FormsiteForm, results: bool = True, items: bool = True) -> None:
        """Save a FormsiteForm to a specific folder in a reliable way

        Args:
            form (FormsiteForm): FormsiteForm instance fetched with use_items=False
            results (bool, optional): Save form results. Defaults to True.
            items (bool, optional): Save form items. Defaults to True.

        Raises:
            FormsiteUncachableParametersException
        """
        if results and not (isinstance(form.data, pd.DataFrame) and form.data.empty):
            folder = f"{self.cache_dir}/results"
            os.makedirs(folder, exist_ok=True)
            items_path = f"{folder}/{form.form_id}_items.json"
            if "id" not in form.data.columns:
                raise FormsiteUncachableParametersException(
                    "Missing 'id' column. Please include it in your results view."
                )
            if form.uses_items is True:
                raise FormsiteUncachableParametersException(
                    "Form was fetched with use_items=True, you must use use_items=False."
                )
            elif form.uses_items is None:
                raise FormsiteUncachableParametersException(
                    "Form was not fetched. Please call form.fetch() first."
                )
            # Store the data
            ext = self.s_format
            data_path = f"{folder}/{form.form_id}_results.{ext}"

            if self.s_format == "feather":
                form.data.to_feather(data_path)
            elif self.s_format == "parquet":
                form.data.to_parquet(data_path)
            elif self.s_format == "hdf":
                form.data.to_hdf(data_path, key=form.form_id)
            elif self.s_format == "json":
                form.data.to_json(data_path, orient="records")
            elif self.s_format == "pickle":
                form.data.to_pickle(data_path)
            elif self.s_format == "csv":
                form.data.to_csv(data_path, encoding="utf-8")

            self.logger.debug(f"Saving form {form.form_id} data in '{data_path}'")

        # ----
        if items and form.items is not None:
            folder = f"{self.cache_dir}/items"
            os.makedirs(folder, exist_ok=True)
            items_path = f"{folder}/{form.form_id}_items.json"

            with open(items_path, "w", encoding="utf-8") as fp:
                json.dump(form.items, fp, indent=4)

            self.logger.debug(f"Saving form {form.form_id} items in '{items_path}'")

    def load(
        self,
        form_id: str,
        results: bool = True,
        items: bool = True,
    ) -> Tuple[pd.DataFrame, list]:
        """Load FormData of this form_id from cache_dir

        Args:
            form_id (str): form id or other unique identifier

        Returns:
            Union[FormData, None]: FormData if it exists in folder, otherwise None
        """
        contents_dict = self.list()
        if form_id not in contents_dict:
            return
        out_results = None
        out_items = None

        # Read saved results
        if results and contents_dict[form_id].get("results") is not None:
            fn = contents_dict[form_id].get("results")
            path = f"{self.cache_dir}/results/{fn}"
            if self.s_format == "fearher":
                out_results = pd.read_feather(path)
            elif self.s_format == "parquet":
                out_results = pd.read_parquet(path)
            elif self.s_format == "hdf":
                out_results = pd.read_hdf(path, key=form_id)
            elif self.s_format == "pickle":
                out_results = pd.read_pickle(path)
            elif self.s_format == "json":
                out_results = pd.read_json(path, orient="records")
            elif self.s_format == "csv":
                out_results = pd.read_csv(path, encoding="utf-8")
            self.logger.debug(f"Loaded {form_id} results from '{path}'")

        # Read saved items
        if items and contents_dict[form_id].get("items") is not None:
            fn = contents_dict[form_id].get("items")
            path = f"{self.cache_dir}/items/{fn}"
            with open(path, "r", encoding="utf-8") as fp:
                out_items = json.load(fp)
            self.logger.debug(f"Loaded {form_id} items from '{path}'")

        return out_results, out_items

    def list(self) -> dict:
        """Lists all form_ids of forms in cache cache_dir

        Returns:
            {form_id: {results: ..., items: ...}, ...}
        """
        out = defaultdict(default_factory={})
        # --- List results
        if os.path.exists(f"{self.cache_dir}/results"):
            for f in os.listdir(f"{self.cache_dir}/results"):
                if f.endswith(f"_results.{self.s_format}"):
                    fid = f.split("_")[0]
                    out[fid]["results"] = f
        # --- List items
        if os.path.exists(f"{self.cache_dir}/items"):
            for f in os.listdir(f"{self.cache_dir}/items"):
                if f.endswith("_items.json"):
                    out[fid]["items"] = f

        return out
