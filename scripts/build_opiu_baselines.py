from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


MXL_PREFIX_SIZE = 13
MXL_COLUMNS = (
    "simplified_formula_code",
    "name",
    "description",
    "accounting_object",
    "ib_register",
    "account",
    "calculation_destination",
    "corresponding_account",
    "calculation_consumer",
    "acquisition_method",
    "usage_method",
    "code",
    "not_used",
)
MXL_CELL = re.compile(
    r'\{16,\d+,\s*\{1,(0|1)(?:,\s*\{"#","((?:\\.|[^"\\])*)"\})?\s*\},0\}'
)
HIERARCHY_FILTER = re.compile(r"(?:К?С\d+) В ИЕРАРХИИ\(([^)]+)\)")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_mxl(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if not raw.startswith(b"MOXCEL"):
        raise ValueError("Ожидался MXL-контейнер MOXCEL")
    text = raw[MXL_PREFIX_SIZE:].decode("utf-8").lstrip("\ufeff")
    cells: list[str] = []
    for match in MXL_CELL.finditer(text):
        escaped = match.group(2) or ""
        try:
            json_string = (
                escaped.replace("\r", "\\r")
                .replace("\n", "\\n")
                .replace("\t", "\\t")
            )
            cells.append(json.loads(f'"{json_string}"'))
        except json.JSONDecodeError as exc:
            raise ValueError("MXL содержит неподдерживаемое экранирование") from exc
    width = len(MXL_COLUMNS)
    table_cell_count = (len(cells) // width) * width
    rows = [
        cells[index : index + width]
        for index in range(0, table_cell_count, width)
    ]
    if rows[0][0].strip() != "Код упрощенной формулы":
        raise ValueError("Не найдена ожидаемая структурная шапка MXL")
    return [
        {
            "source_row": source_row,
            **{column: value.strip() for column, value in zip(MXL_COLUMNS, row)},
        }
        for source_row, row in enumerate(rows[1:], start=2)
    ]


def full_article_path(expense_type: str, expense_group: str, article: str) -> str:
    return " → ".join(part.strip() for part in (expense_type, expense_group, article))


def derive_article_indicators(
    erp_articles: list[dict[str, Any]],
    report_indicators: list[dict[str, Any]],
    formulas: list[dict[str, Any]],
    analytics: list[dict[str, Any]],
    source_rules: list[dict[str, Any]],
) -> list[dict[str, str]]:
    display_by_destination: dict[str, set[str]] = {}
    for row in report_indicators:
        fields = row.get("fields", {})
        destination = str(fields.get("A", "")).strip()
        display = str(fields.get("T", "")).strip()
        if destination and display:
            display_by_destination.setdefault(destination, set()).add(display)

    formula_by_line: dict[str, set[str]] = {}
    for row in formulas:
        line = str(row.get("line", "")).strip()
        formula = str(row.get("formula", "")).strip()
        if line and formula:
            formula_by_line.setdefault(line, set()).add(formula)

    analytics_by_line: dict[str, set[str]] = {}
    for row in analytics:
        line = str(row.get("line", "")).strip()
        values = " | ".join(str(value).strip() for value in row.get("analytics", []) if str(value).strip())
        if line and values:
            analytics_by_line.setdefault(line, set()).add(values)

    destinations_by_hierarchy: dict[str, set[str]] = {}
    selections_by_pair: dict[tuple[str, str], set[str]] = {}
    for row in source_rules:
        selection = row["simplified_formula_code"]
        destination = row["calculation_destination"]
        if not destination or "Запад" in destination:
            continue
        for hierarchy in HIERARCHY_FILTER.findall(selection):
            hierarchy = hierarchy.strip()
            destinations_by_hierarchy.setdefault(hierarchy, set()).add(destination)
            selections_by_pair.setdefault((hierarchy, destination), set()).add(selection)

    exact_target: dict[str, tuple[str, str, str]] = {}
    for hierarchy, destinations in destinations_by_hierarchy.items():
        candidates: list[tuple[str, str]] = []
        for destination in sorted(destinations):
            displays = display_by_destination.get(destination, set())
            if len(displays) == 1:
                candidates.append((destination, next(iter(displays))))
        if len(candidates) != 1:
            continue
        destination, display = candidates[0]
        selections = selections_by_pair[(hierarchy, destination)]
        # The complete account/corresponding-account selections stay in
        # opiu_source_rules.json. The active rule records the exact hierarchy
        # predicate used to prove the group relation without duplicating the
        # full source catalog for every leaf ERP article.
        hierarchy_predicates = sorted(
            {
                match.group(0)
                for selection in selections
                for match in re.finditer(
                    rf"(?:К?С\d+) В ИЕРАРХИИ\({re.escape(hierarchy)}\)", selection
                )
            }
        )
        exact_target[hierarchy] = (
            display,
            " | ".join(hierarchy_predicates),
            next(iter(analytics_by_line.get(display, {""})))
            if len(analytics_by_line.get(display, set())) <= 1
            else "",
        )

    result: list[dict[str, str]] = []
    for article in erp_articles:
        expense_type = str(article.get("expense_type", "")).strip()
        expense_group = str(article.get("expense_group", "")).strip()
        article_name = str(article.get("source_article", "")).strip()
        # A disclosure group is mandatory for this evidence-backed path.
        if not expense_group or expense_type not in exact_target:
            continue
        indicator, formula_condition, indicator_analytics = exact_target[expense_type]
        result.append(
            {
                "erp_code": "",
                "article_path": full_article_path(
                    expense_type, expense_group, article_name
                ),
                "article_name": article_name,
                "indicator": indicator,
                # None of the supplied expense sources contains a sales-channel
                # value. Keep it empty so Preview asks for attention rather than
                # inventing a reference value.
                "sales_channel": "",
                "indicator_type": "EXPENSE",
                "revenue_group": "",
                "formula_condition": formula_condition,
                "analytics": indicator_analytics,
                "nomenclature": "",
                "unit": "",
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build packaged OPIU reference baselines from exact owner sources."
    )
    parser.add_argument("--extracted-dir", type=Path, required=True)
    parser.add_argument("--mxl", type=Path, required=True)
    parser.add_argument("--erp-articles", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    formulas = read_json(args.extracted_dir / "opiu_formulas.json")
    analytics = read_json(args.extracted_dir / "opiu_analytics.json")
    regions = read_json(args.extracted_dir / "regions.json")
    networks = read_json(args.extracted_dir / "sales_networks.json")
    report_indicators = read_json(
        args.extracted_dir / "opiu_report_indicators.json"
    )
    source_rules = parse_mxl(args.mxl)
    erp_articles = read_json(args.erp_articles)
    article_indicators = derive_article_indicators(
        erp_articles,
        report_indicators,
        formulas,
        analytics,
        source_rules,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "article_indicators.json": article_indicators,
        "opiu_formulas.json": formulas,
        "opiu_analytics.json": analytics,
        "regions.json": regions,
        "sales_networks.json": networks,
        "opiu_report_indicators.json": report_indicators,
        "opiu_source_rules.json": source_rules,
    }
    for name, payload in payloads.items():
        write_json(args.output_dir / name, payload)

    print(
        json.dumps(
            {
                "counts": {name.removesuffix(".json"): len(payload) for name, payload in payloads.items()},
                "mxl_sha256": sha256(args.mxl),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
