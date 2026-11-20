import os
import io
import shutil
import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ..auth.permissions import Permission, require_permissions

from .data_loader import (
    DEFAULT_DATA_DIR,
    get_data_path,
    load_sales_data,
    load_costs_data,
    load_funnel_data,
    load_events_data,
)

datasets_router = APIRouter(prefix="/api/datasets", tags=["datasets"])

DATASET_CONFIGS = {
    "sales": {
        "id": "sales",
        "name": "Sales Transactions",
        "description": "Daily unit sales and revenue breakdown by product catalog across reporting periods.",
        "filename": "sales.csv",
        "required_columns": ["date", "product_id", "product_name", "units_sold", "revenue"],
        "loader": load_sales_data,
    },
    "costs": {
        "id": "costs",
        "name": "Unit Procurement Costs",
        "description": "Wholesale supplier procurement and unit manufacturing costs for gross margin calculations.",
        "filename": "costs.csv",
        "required_columns": ["product_id", "product_name", "unit_cost"],
        "loader": load_costs_data,
    },
    "funnel": {
        "id": "funnel",
        "name": "Website Conversion Funnel",
        "description": "Daily e-commerce visitor conversion funnel segmented by desktop and mobile devices.",
        "filename": "website_funnel.csv",
        "required_columns": ["date", "device", "visitors", "reached_cart", "reached_payment", "purchased"],
        "loader": load_funnel_data,
    },
    "events": {
        "id": "events",
        "name": "System & Business Events",
        "description": "Operational event log including software deployments, error alerts, marketing campaigns, and incidents.",
        "filename": "events.csv",
        "required_columns": ["timestamp", "event_type", "description", "affected_system"],
        "loader": load_events_data,
    },
}


class DatasetColumnInfo(BaseModel):
    name: str
    data_type: str
    required: bool
    sample_values: List[Any] = Field(default_factory=list)
    missing_count: int = 0


class DatasetSummary(BaseModel):
    id: str
    name: str
    description: str
    filename: str
    file_path: str
    record_count: int
    file_size_bytes: int
    last_modified: Optional[str]
    status: str
    columns: List[DatasetColumnInfo]
    source_type: str = "CSV File"
    version: int = 1
    last_reloaded_at: Optional[str] = None
    content_hash: Optional[str] = None


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    name: str
    record_count: int
    columns: List[DatasetColumnInfo]
    rows: List[Dict[str, Any]]
    total_columns: int
    duplicate_rows_count: int


class ValidationMessage(BaseModel):
    type: str = "error"  # "error" | "warning"
    field: Optional[str] = None
    message: str
    row_index: Optional[int] = None


class DatasetValidationRequest(BaseModel):
    content: str = Field(min_length=1, description="Raw CSV content string")
    filename: Optional[str] = None


class DatasetValidationResponse(BaseModel):
    dataset_id: str
    is_valid: bool
    total_rows: int
    errors: List[ValidationMessage]
    warnings: List[ValidationMessage]
    detected_columns: List[str]
    missing_columns: List[str]
    extra_columns: List[str]
    preview_rows: List[Dict[str, Any]]


class DatasetUploadRequest(BaseModel):
    filename: str
    content: str = Field(min_length=1, description="Raw CSV content to write")
    overwrite: Optional[bool] = True


class DatasetUploadResponse(BaseModel):
    status: str
    message: str
    dataset_id: str
    record_count: int
    file_size_bytes: int
    backup_created: bool
    version: int = 1
    reloaded_at: Optional[str] = None


def _inspect_dataframe_columns(df: pd.DataFrame, required_cols: List[str]) -> List[DatasetColumnInfo]:
    col_infos = []
    for col in df.columns:
        dt = str(df[col].dtype)
        if "int" in dt:
            typ = "integer"
        elif "float" in dt:
            typ = "float"
        elif "datetime" in dt or "date" in str(col).lower():
            typ = "date"
        else:
            typ = "string"

        # get sample non-null values
        samples = [
            None if pd.isna(v) else (v.isoformat() if hasattr(v, "isoformat") else v)
            for v in df[col].dropna().head(3).tolist()
        ]
        col_infos.append(
            DatasetColumnInfo(
                name=str(col),
                data_type=typ,
                required=col in required_cols,
                sample_values=samples,
                missing_count=int(df[col].isna().sum()),
            )
        )
    return col_infos


def _build_dataset_summary(dataset_id: str) -> DatasetSummary:
    from .dataset_tracker import default_dataset_tracker
    cfg = DATASET_CONFIGS[dataset_id]
    file_path = get_data_path(cfg["filename"])
    ver = default_dataset_tracker.get_version_info(dataset_id)

    if not os.path.exists(file_path):
        return DatasetSummary(
            id=dataset_id,
            name=cfg["name"],
            description=cfg["description"],
            filename=cfg["filename"],
            file_path=file_path,
            record_count=0,
            file_size_bytes=0,
            last_modified=None,
            status="missing",
            columns=[
                DatasetColumnInfo(name=c, data_type="unknown", required=True, sample_values=[], missing_count=0)
                for c in cfg["required_columns"]
            ],
            source_type="CSV File",
            version=ver.version,
            last_reloaded_at=ver.last_reloaded_at,
            content_hash=ver.content_hash,
        )

    file_size = os.path.getsize(file_path)
    mtime = os.path.getmtime(file_path)
    last_mod_iso = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).isoformat()

    try:
        raw_df = pd.read_csv(file_path)
        record_count = len(raw_df)
        col_infos = _inspect_dataframe_columns(raw_df, cfg["required_columns"])
        
        # Check required columns
        missing_required = set(cfg["required_columns"]) - set(raw_df.columns)
        ds_status = "healthy" if not missing_required else "validation_error"
    except Exception:
        record_count = 0
        col_infos = []
        ds_status = "error"

    return DatasetSummary(
        id=dataset_id,
        name=cfg["name"],
        description=cfg["description"],
        filename=cfg["filename"],
        file_path=file_path,
        record_count=record_count,
        file_size_bytes=file_size,
        last_modified=last_mod_iso,
        status=ds_status,
        columns=col_infos,
        source_type="CSV File",
        version=ver.version,
        last_reloaded_at=ver.last_reloaded_at,
        content_hash=ver.content_hash,
    )


@datasets_router.get(
    "",
    response_model=List[DatasetSummary],
    dependencies=[Depends(require_permissions([Permission.DATASET_VIEW]))],
)
def list_datasets():
    """Retrieve overview and metadata for all available datasets in BizPulse."""
    summaries = []
    for did in DATASET_CONFIGS:
        summaries.append(_build_dataset_summary(did))
    return summaries


@datasets_router.get(
    "/{dataset_id}",
    response_model=DatasetSummary,
    dependencies=[Depends(require_permissions([Permission.DATASET_VIEW]))],
)
def get_dataset(dataset_id: str):
    """Retrieve details for a single dataset by ID."""
    if dataset_id not in DATASET_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found. Available: {list(DATASET_CONFIGS.keys())}")
    return _build_dataset_summary(dataset_id)


@datasets_router.get(
    "/{dataset_id}/preview",
    response_model=DatasetPreviewResponse,
    dependencies=[Depends(require_permissions([Permission.DATASET_VIEW]))],
)
def get_dataset_preview(dataset_id: str, limit: int = 50):
    """Inspect schema and first N rows of a dataset."""
    if dataset_id not in DATASET_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

    cfg = DATASET_CONFIGS[dataset_id]
    file_path = get_data_path(cfg["filename"])

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Dataset file '{cfg['filename']}' not found on disk.")

    raw_df = pd.read_csv(file_path)
    total_records = len(raw_df)
    duplicate_rows = int(raw_df.duplicated().sum())

    col_infos = _inspect_dataframe_columns(raw_df, cfg["required_columns"])

    # Prepare rows preview with NaN conversion
    preview_df = raw_df.head(limit)
    rows: List[Dict[str, Any]] = []
    for _, r in preview_df.iterrows():
        row_dict = {}
        for c in raw_df.columns:
            val = r[c]
            if pd.isna(val):
                row_dict[c] = None
            elif isinstance(val, (datetime.date, datetime.datetime)):
                row_dict[c] = val.isoformat()
            else:
                row_dict[c] = val
        rows.append(row_dict)

    return DatasetPreviewResponse(
        dataset_id=dataset_id,
        name=cfg["name"],
        record_count=total_records,
        columns=col_infos,
        rows=rows,
        total_columns=len(raw_df.columns),
        duplicate_rows_count=duplicate_rows,
    )


def validate_csv_content(dataset_id: str, content: str) -> DatasetValidationResponse:
    """Rigorous schema and sanity checks for dataset CSV content."""
    cfg = DATASET_CONFIGS[dataset_id]
    errors: List[ValidationMessage] = []
    warnings: List[ValidationMessage] = []

    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        return DatasetValidationResponse(
            dataset_id=dataset_id,
            is_valid=False,
            total_rows=0,
            errors=[ValidationMessage(type="error", message=f"Failed to parse CSV: {str(e)}")],
            warnings=[],
            detected_columns=[],
            missing_columns=cfg["required_columns"],
            extra_columns=[],
            preview_rows=[],
        )

    detected_cols = list(df.columns)
    required_cols = cfg["required_columns"]
    missing = [c for c in required_cols if c not in detected_cols]
    extra = [c for c in detected_cols if c not in required_cols]

    if missing:
        for m in missing:
            errors.append(ValidationMessage(type="error", field=m, message=f"Missing required column: '{m}'"))

    if extra:
        for x in extra:
            warnings.append(ValidationMessage(type="warning", field=x, message=f"Unrecognized extra column: '{x}'"))

    if len(df) == 0:
        errors.append(ValidationMessage(type="error", message="Uploaded CSV has no data rows."))

    # Specific dataset validations
    if dataset_id == "sales":
        if "units_sold" in df.columns:
            invalid_units = pd.to_numeric(df["units_sold"], errors="coerce").isna()
            if invalid_units.any():
                errors.append(ValidationMessage(type="error", field="units_sold", message=f"{int(invalid_units.sum())} rows contain non-numeric units_sold"))
            elif (pd.to_numeric(df["units_sold"], errors="coerce") < 0).any():
                warnings.append(ValidationMessage(type="warning", field="units_sold", message="Negative values found in units_sold; will be clamped to 0"))

        if "revenue" in df.columns:
            invalid_rev = pd.to_numeric(df["revenue"], errors="coerce").isna()
            if invalid_rev.any():
                errors.append(ValidationMessage(type="error", field="revenue", message=f"{int(invalid_rev.sum())} rows contain non-numeric revenue"))
            elif (pd.to_numeric(df["revenue"], errors="coerce") < 0).any():
                warnings.append(ValidationMessage(type="warning", field="revenue", message="Negative revenue values found; will be clamped to 0.0"))

        if "date" in df.columns:
            invalid_dates = pd.to_datetime(df["date"], errors="coerce").isna()
            if invalid_dates.any():
                errors.append(ValidationMessage(type="error", field="date", message=f"{int(invalid_dates.sum())} rows have unparseable dates"))

    elif dataset_id == "costs":
        if "unit_cost" in df.columns:
            invalid_costs = pd.to_numeric(df["unit_cost"], errors="coerce").isna()
            if invalid_costs.any():
                errors.append(ValidationMessage(type="error", field="unit_cost", message=f"{int(invalid_costs.sum())} rows contain non-numeric unit_cost"))
            elif (pd.to_numeric(df["unit_cost"], errors="coerce") < 0).any():
                warnings.append(ValidationMessage(type="warning", field="unit_cost", message="Negative unit_cost values found; will be clamped to 0.0"))

    elif dataset_id == "funnel":
        numeric_steps = ["visitors", "reached_cart", "reached_payment", "purchased"]
        for step in numeric_steps:
            if step in df.columns:
                invalid_n = pd.to_numeric(df[step], errors="coerce").isna()
                if invalid_n.any():
                    errors.append(ValidationMessage(type="error", field=step, message=f"{int(invalid_n.sum())} rows have non-numeric {step}"))

        if all(step in df.columns for step in numeric_steps):
            # Check mathematical consistency: visitors >= reached_cart >= reached_payment >= purchased
            for idx, r in df.iterrows():
                try:
                    v = float(r["visitors"])
                    c = float(r["reached_cart"])
                    p = float(r["reached_payment"])
                    buy = float(r["purchased"])
                    if c > v:
                        errors.append(ValidationMessage(type="error", field="reached_cart", row_index=int(idx) + 1, message=f"Row {idx+1}: reached_cart ({c}) exceeds visitors ({v})"))
                    if p > c:
                        errors.append(ValidationMessage(type="error", field="reached_payment", row_index=int(idx) + 1, message=f"Row {idx+1}: reached_payment ({p}) exceeds reached_cart ({c})"))
                    if buy > p:
                        errors.append(ValidationMessage(type="error", field="purchased", row_index=int(idx) + 1, message=f"Row {idx+1}: purchased ({buy}) exceeds reached_payment ({p})"))
                except (ValueError, TypeError):
                    pass

    elif dataset_id == "events":
        if "timestamp" in df.columns:
            invalid_ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").isna()
            if invalid_ts.any():
                errors.append(ValidationMessage(type="error", field="timestamp", message=f"{int(invalid_ts.sum())} rows have unparseable timestamps"))

    # Duplicates check
    dups = int(df.duplicated().sum())
    if dups > 0:
        warnings.append(ValidationMessage(type="warning", message=f"Found {dups} duplicate rows in uploaded file"))

    # Prepare preview rows
    preview_rows = []
    for _, r in df.head(10).iterrows():
        row_dict = {}
        for c in df.columns:
            val = r[c]
            row_dict[c] = None if pd.isna(val) else val
        preview_rows.append(row_dict)

    is_valid = len(errors) == 0

    return DatasetValidationResponse(
        dataset_id=dataset_id,
        is_valid=is_valid,
        total_rows=len(df),
        errors=errors,
        warnings=warnings,
        detected_columns=detected_cols,
        missing_columns=missing,
        extra_columns=extra,
        preview_rows=preview_rows,
    )


@datasets_router.post(
    "/{dataset_id}/validate",
    response_model=DatasetValidationResponse,
    dependencies=[Depends(require_permissions([Permission.DATASET_VIEW]))],
)
def validate_dataset(dataset_id: str, req: DatasetValidationRequest):
    """Validate a CSV file against the schema requirements of the specified dataset."""
    if dataset_id not in DATASET_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    return validate_csv_content(dataset_id, req.content)


@datasets_router.post(
    "/{dataset_id}/upload",
    response_model=DatasetUploadResponse,
    dependencies=[Depends(require_permissions([Permission.DATASET_UPLOAD]))],
)
def upload_dataset(dataset_id: str, req: DatasetUploadRequest):
    """
    Safely upload and replace a dataset CSV file.
    Validates schema first; creates an immutable .bak backup before writing.
    """
    if dataset_id not in DATASET_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

    cfg = DATASET_CONFIGS[dataset_id]
    target_path = get_data_path(cfg["filename"])

    # 1. Validate content
    validation_res = validate_csv_content(dataset_id, req.content)
    if not validation_res.is_valid:
        error_msgs = [e.message for e in validation_res.errors]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV Validation failed with {len(validation_res.errors)} errors: " + "; ".join(error_msgs[:3]),
        )

    # 2. Backup existing file if present
    backup_created = False
    if os.path.exists(target_path):
        backup_path = target_path + ".bak"
        try:
            shutil.copyfile(target_path, backup_path)
            backup_created = True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create dataset backup before upload: {str(e)}")

    # 3. Write new content
    try:
        with open(target_path, "w", encoding="utf-8", newline="") as f:
            f.write(req.content.strip())
    except Exception as e:
        # Attempt to restore backup if write failed
        if backup_created and os.path.exists(target_path + ".bak"):
            shutil.copyfile(target_path + ".bak", target_path)
        raise HTTPException(status_code=500, detail=f"Failed to write CSV dataset: {str(e)}")

    # 4. Verify loader can successfully read the new file
    try:
        loaded_df = cfg["loader"](target_path)
        record_count = len(loaded_df)
    except Exception as e:
        # Restore backup
        if backup_created and os.path.exists(target_path + ".bak"):
            shutil.copyfile(target_path + ".bak", target_path)
        raise HTTPException(
            status_code=500,
            detail=f"Uploaded file failed backend loader check: {str(e)}. Dataset rolled back to previous version.",
        )

    file_size = os.path.getsize(target_path)

    # 5. Notify dataset change tracker and invalidate any registered analytics caches
    from .dataset_tracker import default_dataset_tracker
    ver_info = default_dataset_tracker.notify_dataset_changed(dataset_id, target_path)

    return DatasetUploadResponse(
        status="success",
        message=f"Dataset '{cfg['name']}' uploaded and loaded successfully.",
        dataset_id=dataset_id,
        record_count=record_count,
        file_size_bytes=file_size,
        backup_created=backup_created,
        version=ver_info.version,
        reloaded_at=ver_info.last_reloaded_at,
    )
