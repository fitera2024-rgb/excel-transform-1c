from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


BASELINE_KINDS = (
    "erp_articles",
    "organizations",
    "scenarios",
    "intalev_cfos",
    "article_indicators",
)

OPIU_SUPPORT_KINDS = (
    "opiu_formulas",
    "opiu_analytics",
    "regions",
    "sales_networks",
    "opiu_report_indicators",
    "opiu_source_rules",
)


def load_manifest() -> dict[str, Any]:
    return json.loads(
        files(__package__).joinpath("manifest.json").read_text(encoding="utf-8")
    )


def load_baseline_catalogs() -> dict[str, list[dict[str, Any]]]:
    manifest = load_manifest()
    catalogs: dict[str, list[dict[str, Any]]] = {}
    package = files(__package__)
    for kind in BASELINE_KINDS:
        metadata = manifest["catalogs"].get(kind)
        if not isinstance(metadata, dict):
            raise ValueError(f"Baseline manifest не содержит справочник {kind}")
        payload = json.loads(
            package.joinpath(str(metadata["file"])).read_text(encoding="utf-8")
        )
        if not isinstance(payload, list) or len(payload) != int(metadata["count"]):
            raise ValueError(
                f"Baseline-справочник {kind} не соответствует manifest"
            )
        catalogs[kind] = payload
    return catalogs


def baseline_counts() -> dict[str, int]:
    manifest = load_manifest()
    return {
        kind: int(metadata["count"])
        for kind, metadata in manifest["catalogs"].items()
    }
