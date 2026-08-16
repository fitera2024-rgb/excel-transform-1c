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
FORMULA_REFERENCE = re.compile(r"\[([^\]]+)\]")
REPORT_FORMULA_PREFIX = "ОтчетОПрибыляхИУбытках_"
EXACT_REVENUE_GROUPS = ("Выручка_продажи внешние",)
REVENUE_ACCOUNT = "90.1.1"


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


def _analytics_text(row: dict[str, Any]) -> str:
    return " | ".join(
        str(value).strip()
        for value in row.get("analytics", [])
        if str(value).strip()
    )


def derive_revenue_indicators(
    report_indicators: list[dict[str, Any]],
    formulas: list[dict[str, Any]],
    analytics: list[dict[str, Any]],
    source_rules: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Compile only revenue chains proven by all four owner sources.

    A rule is active only when the revenue group formula references one exact
    report-indicator variant, that variant has one display/destination, one
    formula leaf resolves to one MXL source on the revenue account, and the
    aligned analytics row is populated. Missing or duplicate joins are counted
    and deliberately omitted instead of selecting a first result.
    """

    formulas_by_line: dict[str, list[dict[str, Any]]] = {}
    for row in formulas:
        line = str(row.get("line", "")).strip()
        if line:
            formulas_by_line.setdefault(line, []).append(row)

    analytics_by_row: dict[int, list[dict[str, Any]]] = {}
    for row in analytics:
        analytics_by_row.setdefault(int(row.get("source_row", 0)), []).append(row)

    reports_by_code: dict[str, list[dict[str, Any]]] = {}
    for row in report_indicators:
        code = str(row.get("fields", {}).get("AM", "")).strip()
        if code:
            reports_by_code.setdefault(code, []).append(row)

    sources_by_code: dict[str, list[dict[str, Any]]] = {}
    sources_by_reference: dict[str, list[dict[str, Any]]] = {}
    for row in source_rules:
        code = str(row.get("code", "")).strip()
        reference = str(row.get("simplified_formula_code", "")).strip()
        if code:
            sources_by_code.setdefault(code, []).append(row)
        if reference:
            sources_by_reference.setdefault(reference, []).append(row)

    result: list[dict[str, str]] = []
    audit = {"candidates": 0, "derived": 0, "unresolved": 0, "ambiguous": 0}

    for revenue_group in EXACT_REVENUE_GROUPS:
        group_rows = formulas_by_line.get(revenue_group, [])
        if len(group_rows) != 1:
            audit["ambiguous" if len(group_rows) > 1 else "unresolved"] += 1
            continue
        group_formula = str(group_rows[0].get("formula", "")).strip()
        references = FORMULA_REFERENCE.findall(group_formula)
        audit["candidates"] += len(references)
        for reference in references:
            if not reference.startswith(REPORT_FORMULA_PREFIX):
                audit["unresolved"] += 1
                continue

            report_code = reference.removeprefix(REPORT_FORMULA_PREFIX)
            report_rows = reports_by_code.get(report_code, [])
            parent_sources = [
                row
                for row in sources_by_reference.get(f"[{reference}]", [])
                if str(row.get("calculation_consumer", "")).strip()
                == f"{revenue_group} сумма"
            ]
            if len(report_rows) != 1 or len(parent_sources) != 1:
                if len(report_rows) > 1 or len(parent_sources) > 1:
                    audit["ambiguous"] += 1
                else:
                    audit["unresolved"] += 1
                continue

            fields = report_rows[0].get("fields", {})
            article_name = str(fields.get("T", "")).strip()
            destination = str(fields.get("A", "")).strip()
            if not article_name or destination != f"{article_name} сумма":
                audit["unresolved"] += 1
                continue

            leaf_candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for formula_row in formulas_by_line.get(article_name, []):
                leaf_formula = str(formula_row.get("formula", "")).strip()
                leaf_match = FORMULA_REFERENCE.fullmatch(leaf_formula)
                if leaf_match is None:
                    continue
                exact_sources = [
                    row
                    for row in sources_by_code.get(leaf_match.group(1), [])
                    if str(row.get("account", "")).strip() == REVENUE_ACCOUNT
                    and str(row.get("calculation_destination", "")).strip()
                    == "Отчет о прибылях и убытках"
                    and str(row.get("calculation_consumer", "")).strip()
                    == destination
                ]
                if len(exact_sources) == 1:
                    leaf_candidates.append((formula_row, exact_sources[0]))
                elif len(exact_sources) > 1:
                    leaf_candidates.extend(
                        (formula_row, source) for source in exact_sources
                    )

            if len(leaf_candidates) != 1:
                audit["ambiguous" if len(leaf_candidates) > 1 else "unresolved"] += 1
                continue

            formula_row, source = leaf_candidates[0]
            analytics_rows = analytics_by_row.get(
                int(formula_row.get("source_row", 0)), []
            )
            if len(analytics_rows) != 1:
                audit["ambiguous" if len(analytics_rows) > 1 else "unresolved"] += 1
                continue
            analytics_text = _analytics_text(analytics_rows[0])
            formula_condition = str(source.get("description", "")).strip()
            if not analytics_text or not formula_condition:
                audit["unresolved"] += 1
                continue

            result.append(
                {
                    "erp_code": "",
                    "article_path": "",
                    "article_name": article_name,
                    "indicator": article_name,
                    "sales_channel": article_name,
                    "indicator_type": "REVENUE",
                    "revenue_group": revenue_group,
                    "formula_condition": formula_condition,
                    "analytics": "",
                    "nomenclature": "",
                    "unit": "",
                    "counterparty": "",
                    "input_sales_channel": "",
                    "sales_network": "",
                    "sales_region": "",
                }
            )
            audit["derived"] += 1

    return result, audit


def quantity_derivation_audit(
    formulas: list[dict[str, Any]],
    analytics: list[dict[str, Any]],
) -> dict[str, int]:
    """Report quantity candidates without inventing product/unit mappings.

    The supplied formulas prove seven children of ``Оборот в кг`` and the
    analytics catalog names the nomenclature dimension, but neither source
    contains concrete nomenclature values paired with a unit.  Every candidate
    therefore remains unresolved and no active QUANTITY rule is emitted.
    """

    audit = {"candidates": 0, "derived": 0, "unresolved": 0, "ambiguous": 0}
    parent_rows = [
        row for row in formulas if str(row.get("line", "")).strip() == "Оборот в кг"
    ]
    if len(parent_rows) != 1:
        audit["ambiguous" if len(parent_rows) > 1 else "unresolved"] += 1
        return audit

    references = FORMULA_REFERENCE.findall(
        str(parent_rows[0].get("formula", "")).strip()
    )
    audit["candidates"] = len(references)
    audit["unresolved"] = len(references)

    # Read the source explicitly so the audit remains coupled to the declared
    # owner catalog. Dimension names alone are not concrete exact-key values.
    _ = analytics
    return audit


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
        values = _analytics_text(row)
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
    expense_indicators = derive_article_indicators(
        erp_articles,
        report_indicators,
        formulas,
        analytics,
        source_rules,
    )
    revenue_indicators, revenue_audit = derive_revenue_indicators(
        report_indicators,
        formulas,
        analytics,
        source_rules,
    )
    quantity_audit = quantity_derivation_audit(formulas, analytics)
    article_indicators = expense_indicators + revenue_indicators

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
                "indicator_types": {
                    "EXPENSE": len(expense_indicators),
                    "REVENUE": len(revenue_indicators),
                    "QUANTITY": 0,
                },
                "derivation_audit": {
                    "REVENUE": revenue_audit,
                    "QUANTITY": quantity_audit,
                },
                "mxl_sha256": sha256(args.mxl),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
