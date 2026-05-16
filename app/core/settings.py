import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    ocr_cache_enabled: bool = _as_bool(os.getenv("OCR_CACHE_ENABLED"), default=False)
    ocr_cache_file: Path = Path(os.getenv("OCR_CACHE_FILE", "/app/data/ocr_cache.txt"))


settings = Settings()
