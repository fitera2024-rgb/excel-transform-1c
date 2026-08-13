from __future__ import annotations

import argparse
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path


PACKAGE_NAME = "EXCEL_TO_OPIU_LIGHT_USER"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the local Windows user package.")
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--build-sha", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository = Path(__file__).resolve().parents[1]
    wheel_dir = args.wheel_dir.resolve()
    output_dir = args.output_dir.resolve()
    package_dir = output_dir / PACKAGE_NAME

    if not wheel_dir.is_dir():
        raise SystemExit(f"Wheel directory not found: {wheel_dir}")
    wheels = sorted(wheel_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit("No wheels were produced")
    if not any(path.name.startswith("excel_transform_1c-") for path in wheels):
        raise SystemExit("Application wheel is missing")

    shutil.rmtree(package_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir.mkdir(parents=True)
    (package_dir / "wheels").mkdir()

    user_source = repository / "packaging" / "user"
    shutil.copy2(user_source / "START_SERVICE.cmd", package_dir)
    shutil.copy2(user_source / "README_USER_RU.md", package_dir)

    # Windows PowerShell 5.1 treats a UTF-8 script without BOM as an ANSI file.
    # Write the packaged launcher with BOM so Russian text cannot corrupt parsing.
    ps1_text = (user_source / "START_SERVICE.ps1").read_text(encoding="utf-8")
    (package_dir / "START_SERVICE.ps1").write_text(ps1_text, encoding="utf-8-sig")

    for wheel in wheels:
        shutil.copy2(wheel, package_dir / "wheels" / wheel.name)

    build_text = (
        f"commit={args.build_sha}\n"
        f"built_at={datetime.now(UTC).isoformat()}\n"
        "package=EXCEL_TO_OPIU_LIGHT_USER\n"
    )
    (package_dir / "PACKAGE_BUILD.txt").write_text(build_text, encoding="utf-8")
    (package_dir / "runtime").mkdir()
    (package_dir / "runtime" / "README.txt").write_text(
        "Справочники, сценарии и локальные запуски сохраняются в этой папке.\n",
        encoding="utf-8",
    )

    archive_path = output_dir / f"{PACKAGE_NAME}_{args.build_sha[:12]}.zip"
    archive_path.unlink(missing_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output_dir))

    print(archive_path)


if __name__ == "__main__":
    main()
