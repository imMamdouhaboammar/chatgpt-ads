#!/usr/bin/env python3
"""Verify and stage the exact hash-listed public distribution artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

MAX_FILE_BYTES = 10 * 1024 * 1024


def manifest_entries(source: Path) -> list[tuple[PurePosixPath, bytes]]:
    marker = source / "PUBLIC_PROJECTION.json"
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("reviewed public projection marker is missing")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(files, dict) or not files:
        raise ValueError("reviewed public projection marker is invalid")
    entries: list[tuple[PurePosixPath, bytes]] = []
    for name, expected in sorted(files.items()):
        relative = PurePosixPath(name)
        if not isinstance(name, str) or not isinstance(expected, str) or relative.is_absolute() or "." in relative.parts or ".." in relative.parts or relative.as_posix() != name or "\\" in name or ":" in name:
            raise ValueError("public projection contains an unsafe path")
        path = source.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"artifact file missing or unsafe: {name}")
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"artifact hash mismatch: {name}")
        entries.append((relative, data))
    return entries


def stage(source: Path, destination: Path) -> int:
    entries = manifest_entries(source)
    if destination.exists() or destination.is_symlink():
        raise ValueError("staging destination must not exist")
    destination.mkdir(parents=False)
    for relative, data in entries:
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination / "PUBLIC_PROJECTION.json").write_bytes((source / "PUBLIC_PROJECTION.json").read_bytes())
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            count = len(manifest_entries(args.source.resolve()))
        elif args.out is not None:
            count = stage(args.source.resolve(), args.out.absolute())
        else:
            parser.error("one of --check or --out is required")
        print(json.dumps({"status": "valid", "files": count}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"artifact refused: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
