import os
import hashlib
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel

from .data_loader import DEFAULT_DATA_DIR, get_data_path

logger = logging.getLogger("bizpulse.analytics.dataset_tracker")


class DatasetVersionInfo(BaseModel):
    dataset_id: str
    version: int = 1
    content_hash: str
    last_reloaded_at: Optional[str] = None
    reload_count: int = 0
    status: str = "ready"


class DatasetTracker:
    """
    Central change tracker and invalidation coordinator for BizPulse datasets.
    Maintains thread-safe dataset versioning, content hashes, and change listeners.
    Ensures that when ground-truth CSV datasets are replaced or updated,
    the analytics engine and downstream consumers recognize the change.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self._lock = threading.Lock()
        self._versions: Dict[str, DatasetVersionInfo] = {}
        self._listeners: List[Callable[[str, DatasetVersionInfo], None]] = []
        self._analytics_caches: List[Dict[str, Any]] = []

    def _compute_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of a file on disk."""
        if not os.path.exists(filepath):
            return "missing"
        try:
            hasher = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to compute hash for {filepath}: {e}")
            return "error"

    def get_version_info(self, dataset_id: str) -> DatasetVersionInfo:
        """Get or initialize the current version info for a dataset."""
        with self._lock:
            if dataset_id not in self._versions:
                from .datasets_router import DATASET_CONFIGS
                cfg = DATASET_CONFIGS.get(dataset_id, {})
                filename = cfg.get("filename", f"{dataset_id}.csv")
                filepath = get_data_path(filename, self.data_dir)
                initial_hash = self._compute_hash(filepath)
                self._versions[dataset_id] = DatasetVersionInfo(
                    dataset_id=dataset_id,
                    version=1,
                    content_hash=initial_hash,
                    last_reloaded_at=None,
                    reload_count=0,
                    status="ready",
                )
            return self._versions[dataset_id]

    def notify_dataset_changed(
        self, dataset_id: str, filepath: Optional[str] = None
    ) -> DatasetVersionInfo:
        """
        Record that a dataset file was successfully replaced or reloaded:
        1. Increments version and reload_count.
        2. Recomputes SHA-256 content hash.
        3. Updates last_reloaded_at UTC timestamp.
        4. Invalidates any registered caches.
        5. Notifies registered change listeners.
        """
        with self._lock:
            # Ensure initialized
            if dataset_id not in self._versions:
                from .datasets_router import DATASET_CONFIGS
                cfg = DATASET_CONFIGS.get(dataset_id, {})
                filename = cfg.get("filename", f"{dataset_id}.csv")
                target_path = filepath or get_data_path(filename, self.data_dir)
                initial_hash = self._compute_hash(target_path)
                current = DatasetVersionInfo(
                    dataset_id=dataset_id,
                    version=1,
                    content_hash=initial_hash,
                    last_reloaded_at=None,
                    reload_count=0,
                    status="ready",
                )
            else:
                current = self._versions[dataset_id]

            from .datasets_router import DATASET_CONFIGS
            cfg = DATASET_CONFIGS.get(dataset_id, {})
            filename = cfg.get("filename", f"{dataset_id}.csv")
            target_path = filepath or get_data_path(filename, self.data_dir)
            new_hash = self._compute_hash(target_path)
            now_iso = datetime.now(timezone.utc).isoformat()

            updated = DatasetVersionInfo(
                dataset_id=dataset_id,
                version=current.version + 1,
                content_hash=new_hash,
                last_reloaded_at=now_iso,
                reload_count=current.reload_count + 1,
                status="ready",
            )
            self._versions[dataset_id] = updated

            # Invalidate registered caches
            for c in self._analytics_caches:
                try:
                    c.clear()
                except Exception as e:
                    logger.warning(f"Error clearing cache: {e}")

            # Notify listeners
            for listener in self._listeners:
                try:
                    listener(dataset_id, updated)
                except Exception as e:
                    logger.error(f"Error in dataset change listener: {e}", exc_info=True)

            logger.info(
                f"Dataset '{dataset_id}' reloaded -> version={updated.version}, "
                f"reloads={updated.reload_count}, hash={new_hash[:12]}..."
            )
            return updated

    def register_change_listener(self, listener: Callable[[str, DatasetVersionInfo], None]) -> None:
        """Register a callback to be called whenever a dataset successfully reloads."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def register_cache(self, cache_dict: Dict[str, Any]) -> None:
        """Register an in-memory dictionary cache to be cleared upon dataset reload."""
        with self._lock:
            if cache_dict not in self._analytics_caches:
                self._analytics_caches.append(cache_dict)

    def clear_caches(self) -> None:
        """Manually invalidate all registered analytics caches."""
        with self._lock:
            for c in self._analytics_caches:
                try:
                    c.clear()
                except Exception:
                    pass

    def get_all_versions(self) -> Dict[str, DatasetVersionInfo]:
        """Return version info for all known datasets."""
        from .datasets_router import DATASET_CONFIGS
        return {did: self.get_version_info(did) for did in DATASET_CONFIGS}


# Global singleton instance
default_dataset_tracker = DatasetTracker()
