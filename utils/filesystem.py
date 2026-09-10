import os
import re
import uuid
import shutil
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
import config


def safe_filename(name: str, fallback: str = "track") -> str:
    """
    Sanitizes string for use as a filesystem filename across Windows and Linux.
    Removes invalid characters: \\ / : * ? " < > | and control characters.
    """
    if not name:
        return fallback

    # Remove invalid filesystem characters
    cleaned = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", str(name))
    # Replace multiple spaces/underscores with single space
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned if cleaned else fallback


@contextmanager
def temporary_work_dir() -> Generator[Path, None, None]:
    """
    Creates an isolated unique temporary directory for a single download job.
    Ensures that concurrent downloads never overwrite or delete each other's files.
    Cleans up automatically when the context exits.
    """
    job_id = uuid.uuid4().hex[:10]
    work_dir = config.DOWNLOAD_DIR / f"job_{job_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield work_dir
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
