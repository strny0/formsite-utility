"""

cache.py

"""

import os
from pathlib import Path
from typing import List, Union
import json
from datetime import datetime as dt
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

    def save(self, form: FormsiteForm) -> None:
        """Save a FormsiteForm to a specific folder in a reliable way

        Args:
            form (FormsiteForm)

        Raises:
            FormsiteUncachableParametersException
        """
        if form.uses_items == True:
            raise FormsiteUncachableParametersException(
                "Form was fetched with use_items=True, you must use use_items=False."
            )
        elif form.uses_items == None:
            raise FormsiteUncachableParametersException(
                "Form was not fetched. Please call form.fetch() first."
            )
        if "id" not in form.data.columns:
            raise FormsiteUncachableParametersException(
                "Missing 'id' column. Please include it in your results view."
            )

        os.makedirs(self.cache_dir, exist_ok=True)
        if isinstance(form.data, pd.DataFrame) and form.data.empty:
            return

        # Store the data
        folder = self.cache_dir
        ext = self.s_format
        data_path = f"{folder}/{form.form_id}_data.{ext}"

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

        # Store the metadata
        metadata_path = f"{folder}/{form.form_id}_metadata.json"
        latest_id = max(form.data["id"]) if "id" in form.data.columns else None
        latest_date = (
            max(form.data["data_update"]) if "data_update" in form.data.columns else None
        )

        metadata = {
            "data_path": data_path,
            "update_date_utc": dt.utc_now(),
            "form_id": form.form_id,
            "serialization_format": self.s_format,
            "rows_count": form.data.shape[0],
            "columns_count": form.data.shape[1],
            "latest_result_date": latest_id,
            "latest_result_id": latest_date,
            "items": form.items,
        }

        with open(metadata_path, "w", encoding="utf-8") as fp:
            json.dump(metadata, fp, indent=4)

        # ----
        msg = f"Saving form {form.form_id} data in '{data_path}' metadata in '{metadata_path}'"
        self.logger.debug(msg)

    def load(self, form_id: str) -> Union[FormData, None]:
        """Load FormData of this form_id from cache_dir

        Args:
            form_id (str): form id or other unique identifier

        Returns:
            Union[FormData, None]: FormData if it exists in folder, otherwise None
        """
        if form_id not in self.list():
            return

        # Read saved data
        data_path = f"{self.cache_dir}/{form_id}_data.{self.s_format}"

        if self.s_format == "fearher":
            df = pd.read_feather(data_path)
        elif self.s_format == "parquet":
            df = pd.read_parquet(data_path)
        elif self.s_format == "hdf":
            df = pd.read_hdf(data_path, key=form_id)
        elif self.s_format == "pickle":
            df = pd.read_pickle(data_path)
        elif self.s_format == "json":
            df = pd.read_json(data_path, orient="records")
        elif self.s_format == "csv":
            df = pd.read_csv(data_path, encoding="utf-8")

        # Read saved metadata
        metadata_path = f"{self.cache_dir}/{form_id}_metadata.json"
        with open(metadata_path, "r", encoding="utf-8") as fp:
            metadata = json.load(fp)

        # Create FormData object
        form = FormData()
        form.data = df
        form.items = {"items": metadata.get("items", None)}
        form.uses_items = True

        # ----
        msg = f"Loaded {form_id} data from '{data_path}' metadata from '{metadata_path}'"
        self.logger.debug(msg)

        return form

    def update(self, form: FormsiteForm) -> FormsiteForm:
        """Load old form from cache, merge data with new form, save new data, return combined form

        Args:
            form (FormsiteForm)

        Returns:
            FormsiteForm: New form with combined data and same session object as previous form
        """
        old_data = self.load(form.form_id)
        combined_data = pd.DataFrame()
        if old_data:
            combined_data = pd.concat([form.data, old_data], ignore_index=True)
            combined_data = combined_data.drop_duplicates(subset=["id"], keep="first")
        data = FormData()
        data.data = combined_data
        data.items = form._items
        data._uses_items = form._uses_items
        new_form = FormsiteForm(
            form_id=form.form_id,
            session=form.session,
            data=data,
        )
        self.save(new_form)
        msg = f"Updated cache for {form.form_id}"
        self.logger.debug(msg)
        return new_form

    def list_metadata(self) -> List[dict]:
        """Lists all forms metadata in cache cache_dir"""
        metadata = []
        for f in os.listdir(self.cache_dir):
            if f.endswith("_metadata.json"):
                with open(f"{self.cache_dir}/{f}", "r", encoding="utf-8") as fp:
                    metadata.append(json.load(fp))
        return metadata

    def list(self) -> List[str]:
        """Lists all form_ids of forms in cache cache_dir"""
        data = set()
        metadata = set()
        for f in os.listdir(self.cache_dir):
            if f.endswith(f"_data.{self.s_format}"):
                data.add(f.split("_")[0])
            if f.endswith("_metadata.json"):
                metadata.add(f.split("_")[0])

        form_ids = data.intersection(metadata)
        return sorted(list(form_ids))
