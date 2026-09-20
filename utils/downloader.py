import time
import requests
from typing import Callable, Optional
from pathlib import Path
import config


def download_stream(
    url: str,
    target_path: Path,
    on_progress: Optional[Callable[[int, int, int], None]] = None,
    interval: float = config.PROGRESS_UPDATE_INTERVAL,
    max_bytes: Optional[int] = config.MAX_AUDIO_BYTES,
) -> int:
    """
    Downloads a file with streaming, size guards, and throttled progress reporting.

    :param url: File download URL.
    :param target_path: Path to write the downloaded file.
    :param on_progress: Optional callback function with signature (downloaded_bytes, total_bytes, percent).
    :param interval: Minimum time in seconds between progress callback invocations.
    :param max_bytes: Maximum allowed bytes to download before aborting (prevents disk-fill DoS).
    :return: Total downloaded bytes.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    with requests.get(url, stream=True, headers=headers, timeout=config.NETWORK_TIMEOUT) as response:
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        if max_bytes and total_size > max_bytes:
            raise ValueError(
                f"File size ({total_size / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of {max_bytes / (1024 * 1024):.1f} MB."
            )

        downloaded = 0
        last_callback_time = 0.0

        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if max_bytes and downloaded > max_bytes:
                        raise ValueError(
                            f"Download exceeded maximum allowed limit of {max_bytes / (1024 * 1024):.1f} MB."
                        )

                    now = time.time()
                    if on_progress and (now - last_callback_time >= interval):
                        percent = int((downloaded / total_size) * 100) if total_size > 0 else 0
                        try:
                            on_progress(downloaded, total_size, percent)
                        except Exception:
                            pass
                        last_callback_time = now

        # Final progress callback at 100%
        if on_progress:
            try:
                on_progress(downloaded, total_size, 100)
            except Exception:
                pass

        return downloaded
