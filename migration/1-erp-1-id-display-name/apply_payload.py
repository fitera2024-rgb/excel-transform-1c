from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile

EXPECTED_SHA256 = "990f565d703751df4ee8768440e29dac3b878cccf7f3b3baa5333d9d0476c006"
EXPECTED_PATHS = {
    "src/excel_transform_1c/adapters/persistence.py",
    "src/excel_transform_1c/adapters/references.py",
    "src/excel_transform_1c/baselines/__init__.py",
    "src/excel_transform_1c/baselines/erp_articles.json",
    "src/excel_transform_1c/baselines/intalev_cfos.json",
    "src/excel_transform_1c/baselines/manifest.json",
    "src/excel_transform_1c/baselines/organizations.json",
    "src/excel_transform_1c/baselines/scenarios.json",
}


def main() -> int:
    handoff_dir = Path(__file__).resolve().parent
    repo_root = handoff_dir.parents[1]
    parts = sorted(handoff_dir.glob("payload.b64.part-*.txt"))
    if not parts:
        raise RuntimeError("Payload parts not found")

    encoded = "".join(part.read_text(encoding="ascii") for part in parts)
    payload = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"Payload SHA-256 mismatch: {digest}")

    with tempfile.TemporaryDirectory(prefix="codex-handoff-") as temp_dir:
        archive_path = Path(temp_dir) / "payload.tar.xz"
        archive_path.write_bytes(payload)
        with tarfile.open(archive_path, mode="r:xz") as archive:
            members = [member for member in archive.getmembers() if member.isfile()]
            names = {member.name for member in members}
            if names != EXPECTED_PATHS:
                raise RuntimeError(
                    "Unexpected payload paths: "
                    f"missing={sorted(EXPECTED_PATHS - names)}, "
                    f"extra={sorted(names - EXPECTED_PATHS)}"
                )
            for member in sorted(members, key=lambda item: item.name):
                destination = (repo_root / member.name).resolve()
                if repo_root.resolve() not in destination.parents:
                    raise RuntimeError(f"Unsafe payload path: {member.name}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"Cannot read payload path: {member.name}")
                with source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)

    print("Applied exact payload files:")
    for path in sorted(EXPECTED_PATHS):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
