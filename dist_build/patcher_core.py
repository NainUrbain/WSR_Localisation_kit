"""Hash-guarded, line-delta patch engine used by both WSR_KR builds."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != 1:
        raise RuntimeError("Unsupported patch manifest format.")
    return data


def apply_entry(app_dir: Path, entry: dict) -> str:
    target = app_dir / entry["path"]
    raw = target.read_bytes()
    digest = sha256(raw)
    if digest == entry["patched_sha256"]:
        return "already-patched"
    if digest != entry["original_sha256"]:
        raise RuntimeError(
            f"Unsupported game version or modified file: {entry['path']}\n"
            f"Current SHA256: {digest}\nRun Steam's file-integrity verification and try again."
        )

    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    for hunk in reversed(entry["hunks"]):
        start = hunk["start_line"]
        end = start + hunk["delete_count"]
        old = "".join(lines[start:end]).encode("utf-8")
        if sha256(old) != hunk["original_sha256"]:
            raise RuntimeError(f"Patch context verification failed: {entry['path']}:{start + 1}")
        lines[start:end] = hunk["new_text"].splitlines(keepends=True)

    result = "".join(lines).encode("utf-8")
    if sha256(result) != entry["patched_sha256"]:
        raise RuntimeError(f"Patched-file verification failed: {entry['path']}")
    target.write_bytes(result)
    return "patched"


def verify_entry(app_dir: Path, entry: dict) -> bool:
    target = app_dir / entry["path"]
    return target.is_file() and sha256(target.read_bytes()) == entry["patched_sha256"]
