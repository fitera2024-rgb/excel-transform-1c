from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from excel_transform_1c.core.detection import normalize_header
from excel_transform_1c.core.models import ERPArticle, OrganizationNode


ERP_HEADERS = {
    "code": {"код"},
    "name": {"официальное наименование", "наименование erp"},
    "expense_type": {"тип расходов"},
    "expense_group": {"группа расходов"},
    "source_article": {"статья", "исходная статья"},
}

ORG_HEADERS = {
    "node_id": {"id", "идентификатор"},
    "code": {"код"},
    "name": {"наименование", "узел"},
    "parent_id": {"родитель id", "parent id"},
    "full_path": {"полный путь", "путь"},
}

SCENARIO_HEADERS = {
    "name": {"наименование", "сценарий"},
    "year": {"год"},
    "erp_code": {"erp-код", "код"},
    "comment": {"комментарий"},
}

REAL_ERP_HEADERS = {
    "hierarchy_name": {"статья доходов и расходов"},
    "code": {"код"},
}

REAL_ORG_REQUIRED_HEADERS = {
    "name": {"организация", "организации"},
    "code": {"код"},
}

REAL_ORG_OPTIONAL_HEADERS = {
    "parent": {"родитель", "родительский узел", "родительская организация"},
    "full_path": {"полный путь", "путь", "полное наименование"},
}

REAL_SCENARIO_REQUIRED_HEADERS = {
    "name": {"сценарий", "сценарии"},
    "erp_code": {"код", "erp-код"},
}

REAL_SCENARIO_OPTIONAL_HEADERS = {
    "year": {"год"},
    "comment": {"комментарий"},
}


def parse_reference_workbook(content: bytes, kind: str) -> list[dict[str, Any]]:
    workbook = load_workbook(BytesIO(content), data_only=True, read_only=False)
    if kind == "erp_articles":
        return _parse_erp_articles(workbook)
    if kind == "organizations":
        return _parse_organizations(workbook)
    if kind == "scenarios":
        return _parse_scenarios(workbook)
    raise ValueError("Неизвестный тип справочника")


def _parse_erp_articles(workbook: Any) -> list[dict[str, Any]]:
    flat = _single_range(workbook, ERP_HEADERS)
    if flat:
        return _flat_rows(*flat)

    sheet, header_row, columns = _require_single_range(workbook, REAL_ERP_HEADERS)
    name_column = columns["hierarchy_name"]
    code_column = columns["code"]
    stack: dict[int, str] = {}
    rows: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for row_number in range(header_row + 1, sheet.max_row + 1):
        name_cell = sheet.cell(row_number, name_column)
        name = _text(name_cell.value)
        if name:
            level = _hierarchy_level(name_cell)
            stack = {key: value for key, value in stack.items() if key < level}
            stack[level] = name.strip()
        code = _text(sheet.cell(row_number, code_column).value).strip()
        if not code:
            continue
        path = [stack[key] for key in sorted(stack)]
        if len(path) < 2:
            raise ValueError("ERP-справочник содержит код без полного иерархического пути")
        if code in seen_codes:
            raise ValueError("ERP-справочник содержит повторяющийся код")
        seen_codes.add(code)
        source_article = path[-1]
        rows.append(
            {
                "code": code,
                "name": source_article,
                "expense_type": path[0],
                "expense_group": path[-2] if len(path) >= 3 else "",
                "source_article": source_article,
            }
        )
    if not rows:
        raise ValueError("ERP-справочник не содержит кодированных статей")
    return rows


def _parse_organizations(workbook: Any) -> list[dict[str, Any]]:
    flat = _single_range(workbook, ORG_HEADERS)
    if flat:
        return _flat_rows(*flat)

    sheet, header_row, columns = _require_single_range(
        workbook,
        REAL_ORG_REQUIRED_HEADERS,
        REAL_ORG_OPTIONAL_HEADERS,
    )
    raw: list[dict[str, str | int | None]] = []
    stack: dict[int, dict[str, str]] = {}
    for row_number in range(header_row + 1, sheet.max_row + 1):
        name_cell = sheet.cell(row_number, columns["name"])
        name = _text(name_cell.value).strip()
        code = _text(sheet.cell(row_number, columns["code"]).value).strip()
        if not name and not code:
            continue
        if not name or not code:
            continue
        level = _hierarchy_level(name_cell)
        stack = {key: value for key, value in stack.items() if key < level}
        parent = _text(sheet.cell(row_number, columns["parent"]).value).strip() if "parent" in columns else ""
        full_path = (
            _text(sheet.cell(row_number, columns["full_path"]).value).strip()
            if "full_path" in columns
            else ""
        )
        parent_from_tree = stack[max(stack)]["code"] if stack else ""
        path_from_tree = " → ".join([stack[key]["name"] for key in sorted(stack)] + [name])
        raw.append(
            {
                "node_id": code,
                "code": code,
                "name": name,
                "parent": parent,
                "parent_from_tree": parent_from_tree,
                "full_path": full_path or path_from_tree,
            }
        )
        stack[level] = {"code": code, "name": name}

    if not raw:
        raise ValueError("Справочник организаций не содержит кодированных узлов")
    by_code = {str(item["code"]): str(item["node_id"]) for item in raw}
    by_path = {str(item["full_path"]): str(item["node_id"]) for item in raw}
    by_unique_name: dict[str, str] = {}
    name_counts: dict[str, int] = {}
    for item in raw:
        name = str(item["name"])
        name_counts[name] = name_counts.get(name, 0) + 1
        by_unique_name[name] = str(item["node_id"])

    result: list[dict[str, Any]] = []
    for item in raw:
        parent_value = str(item["parent"] or "")
        parent_id = (
            by_code.get(parent_value)
            or by_path.get(parent_value)
            or (by_unique_name.get(parent_value) if name_counts.get(parent_value) == 1 else None)
            or str(item["parent_from_tree"] or "")
        )
        result.append(
            {
                "node_id": str(item["node_id"]),
                "code": str(item["code"]),
                "name": str(item["name"]),
                "parent_id": parent_id,
                "full_path": str(item["full_path"]),
            }
        )
    return result


def _parse_scenarios(workbook: Any) -> list[dict[str, Any]]:
    flat = _single_range(workbook, SCENARIO_HEADERS)
    if flat:
        return _flat_rows(*flat)

    sheet, header_row, columns = _require_single_range(
        workbook,
        REAL_SCENARIO_REQUIRED_HEADERS,
        REAL_SCENARIO_OPTIONAL_HEADERS,
    )
    rows: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, sheet.max_row + 1):
        name = _text(sheet.cell(row_number, columns["name"]).value).strip()
        if not name:
            continue
        erp_code = _text(sheet.cell(row_number, columns["erp_code"]).value).strip()
        explicit_year = _text(sheet.cell(row_number, columns["year"]).value).strip() if "year" in columns else ""
        year_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", name.replace("_", " "))
        year = explicit_year or (year_match.group(1) if year_match else "0")
        comment = _text(sheet.cell(row_number, columns["comment"]).value).strip() if "comment" in columns else ""
        rows.append({"name": name, "year": year, "erp_code": erp_code, "comment": comment})
    if not rows:
        raise ValueError("Справочник сценариев не содержит записей")
    return rows


def _single_range(
    workbook: Any,
    required: dict[str, set[str]],
    optional: dict[str, set[str]] | None = None,
) -> tuple[Any, int, dict[str, int]] | None:
    candidates = _find_ranges(workbook, required, optional)
    return candidates[0] if len(candidates) == 1 else None


def _require_single_range(
    workbook: Any,
    required: dict[str, set[str]],
    optional: dict[str, set[str]] | None = None,
) -> tuple[Any, int, dict[str, int]]:
    candidates = _find_ranges(workbook, required, optional)
    if len(candidates) != 1:
        raise ValueError("Справочник должен содержать ровно один структурно распознаваемый диапазон")
    return candidates[0]


def _find_ranges(
    workbook: Any,
    required: dict[str, set[str]],
    optional: dict[str, set[str]] | None = None,
) -> list[tuple[Any, int, dict[str, int]]]:
    candidates: list[tuple[Any, int, dict[str, int]]] = []
    for sheet in workbook.worksheets:
        for row_number in range(1, min(sheet.max_row, 50) + 1):
            values = [cell.value for cell in sheet[row_number]]
            columns = _match_headers(values, required, optional)
            if columns:
                candidates.append((sheet, row_number, columns))
    return candidates


def _flat_rows(sheet: Any, header_row: int, columns: dict[str, int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, sheet.max_row + 1):
        item = {field: sheet.cell(row_number, column).value for field, column in columns.items()}
        if all(value is None for value in item.values()):
            continue
        rows.append({field: _text(value) for field, value in item.items()})
    return rows


def _match_headers(
    values: list[Any],
    required: dict[str, set[str]],
    optional: dict[str, set[str]] | None = None,
) -> dict[str, int] | None:
    normalized = {index: normalize_header(value) for index, value in enumerate(values, start=1)}
    columns: dict[str, int] = {}
    for field, aliases in required.items():
        matches = [index for index, value in normalized.items() if value in {normalize_header(alias) for alias in aliases}]
        if len(matches) != 1:
            return None
        columns[field] = matches[0]
    for field, aliases in (optional or {}).items():
        matches = [index for index, value in normalized.items() if value in {normalize_header(alias) for alias in aliases}]
        if len(matches) == 1:
            columns[field] = matches[0]
    return columns


def _hierarchy_level(cell: Any) -> int:
    indent = int(cell.alignment.indent or 0)
    if indent:
        return indent
    text = _text(cell.value)
    leading = len(text) - len(text.lstrip())
    return leading // 2


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def erp_articles(payload: list[dict[str, Any]]) -> list[ERPArticle]:
    return [ERPArticle(**item) for item in payload]


def organization_nodes(payload: list[dict[str, Any]]) -> list[OrganizationNode]:
    return [
        OrganizationNode(
            node_id=item["node_id"],
            code=item["code"],
            name=item["name"],
            parent_id=item["parent_id"] or None,
            full_path=item["full_path"],
        )
        for item in payload
    ]
