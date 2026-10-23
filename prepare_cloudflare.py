"""Prepare Guardian's Python Worker from the companion ZIP in Workers Builds.

Upload this file and Guardian-Telegram-Bot.zip to the repository root.
Create D1 separately and add its UUID as build variable D1_DATABASE_ID.
Optional build variables: WORKER_NAME (default dlb-moder-bot),
D1_DATABASE_NAME (default guardian-moderation).

Build command:
  python prepare_cloudflare.py && python -m venv .build-tools && .build-tools/bin/pip install uv==0.12.23 && .build-tools/bin/uv sync --directory .guardian-build --locked
Deploy command:
  .build-tools/bin/uv run --directory .guardian-build pywrangler deploy

This only prepares files. D1 schema, runtime secrets and Telegram webhook
must still be configured. No credentials belong in this file or the ZIP.
"""

import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from uuid import UUID
from zipfile import ZipFile

ARCHIVE_SHA256 = "a9aec418d1fafb00b9a7904ab858e10c54d1f3c60d731b173f82912b83fa327a"
PREFIX = "guardian-bot/cloudflare/"


def prepare(root: Path) -> Path:
    database_id = os.environ.get("D1_DATABASE_ID", "").strip()
    try:
        parsed = UUID(database_id)
        if parsed.int == 0:
            raise ValueError
    except ValueError:
        raise SystemExit("Set build variable D1_DATABASE_ID to the UUID of your D1 database.")
    worker_name = os.environ.get("WORKER_NAME", "dlb-moder-bot").strip()
    database_name = os.environ.get("D1_DATABASE_NAME", "guardian-moderation").strip()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", worker_name):
        raise SystemExit("WORKER_NAME must use lowercase letters, digits and hyphens.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,63}", database_name):
        raise SystemExit("Invalid D1_DATABASE_NAME.")
    archive = root / "Guardian-Telegram-Bot.zip"
    if not archive.is_file():
        raise SystemExit("Upload Guardian-Telegram-Bot.zip beside prepare_cloudflare.py.")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise SystemExit("ZIP version mismatch: use the companion archive supplied with this script.")
    output = root / ".guardian-build"
    with ZipFile(archive) as zipped:
        for item in zipped.infolist():
            if item.is_dir() or not item.filename.startswith(PREFIX):
                continue
            relative = PurePosixPath(item.filename[len(PREFIX):])
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit("Unsafe archive path.")
            target = output.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(item))
    config_path = output / "wrangler.jsonc"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["name"] = worker_name
    config["d1_databases"] = [{"binding": "DB", "database_name": database_name,
                               "database_id": str(parsed)}]
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("Python Worker prepared in .guardian-build. Runtime secrets are configured separately.")
    return output


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parent)
