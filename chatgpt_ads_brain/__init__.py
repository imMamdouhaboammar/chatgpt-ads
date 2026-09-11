"""ChatGPT Ads local knowledge and read-only account tools."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib

_source_metadata = Path(__file__).resolve().parents[1] / "pyproject.toml"
if _source_metadata.is_file():
    __version__ = tomllib.loads(_source_metadata.read_text(encoding="utf-8"))["project"]["version"]
else:
    try:
        __version__ = version("chatgpt-ads-brain")
    except PackageNotFoundError:
        __version__ = "unknown"
