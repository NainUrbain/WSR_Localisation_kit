"""Generate compact line-delta manifests without redistributing vanilla files."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entry(rel: str, original: Path, modified: Path) -> dict:
    old_raw, new_raw = original.read_bytes(), modified.read_bytes()
    old = old_raw.decode("utf-8").splitlines(keepends=True)
    new = new_raw.decode("utf-8").splitlines(keepends=True)
    hunks = []
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        removed = "".join(old[a0:a1]).encode("utf-8")
        hunks.append({
            "start_line": a0,
            "delete_count": a1 - a0,
            "original_sha256": digest(removed),
            "new_text": "".join(new[b0:b1]),
        })
    return {"path": rel, "original_sha256": digest(old_raw),
            "patched_sha256": digest(new_raw), "hunks": hunks}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("developer", "player"))
    parser.add_argument("--vanilla", type=Path, required=True)
    parser.add_argument("--modified", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    result = {"format": 1, "mode": args.mode, "files": [
        entry(rel, args.vanilla / rel, args.modified / rel) for rel in args.files
    ]}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
