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

REAL_EXPORT_HEADERS = {
    "erp_articles": {
        "name": {"статья доходов и расходов"},
        "code": {"код"},
    },
    "organizations": {
        "name": {"организации", "организация", "наименование"},
        "code": {"код"},
    },
    "scenarios": {
        "name": {"сценарии", "сценарий", "наименование"},
        "code": {"код"},
    },
}

PATH_ALIASES = {"полный путь", "путь", "иерархия"}


def parse_reference_workbook(content: bytes, kind: str) -> list[dict[str, Any]]:
    if kind not in {"erp_articles", "organizations", "scenarios"}:
        raise ValueError("Неизвестный тип справочника")

    try:
        workbook = load_workbook(BytesIO(content), data_only=True, read_only=False)
    except Exception as exc:
        raise ValueError("Файл справочника не открывается или повреждён") from exc

    flat = _parse_flat_interchange(workbook, kind)
    if flat is not None:
        return flat

    if kind == "erp_articles":
        result = _parse_real_erp_articles(workbook)
    elif kind == "organizations":
        result = _parse_real_organizations(workbook)
    else:
        result = _parse_real_scenarios(workbook)

    if not result:
        raise ValueError(
            "Не найден распознаваемый диапазон справочника. "
            "Загрузите известную ERP-выгрузку либо документированный плоский interchange-файл."
        )
    return result


def _parse_flat_interchange(workbook: Any, kind: str) -> list[dict[str, Any]] | None:
    required = {
        "erp_articles": ERP_HEADERS,
        "organizations": ORG_HEADERS,
        "scenarios": SCENARIO_HEADERS,
    }[kind]
    candidates: list[tuple[Any, int, dict[str, int]]] = []
    for sheet in workbook.worksheets:
        for row_number in range(1, min(sheet.max_row, 80) + 1):
            values = [cell.value for cell in sheet[row_number]]
            columns = _match_headers(values, required)
            if columns:
                candidates.append((sheet, row_number, columns))
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError("Справочник содержит несколько плоских структурно подходящих диапазонов")

    sheet, header_row, columns = candidates[0]
    rows: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, sheet.max_row + 1):
        item = {field: sheet.cell(row_number, column).value for field, column in columns.items()}
        if all(_is_blank(value) for value in item.values()):
            continue
        rows.append(
            {
                field: _clean_flat_value(field, value)
                for field, value in item.items()
            }
        )
    return rows


def _parse_real_erp_articles(workbook: Any) -> list[dict[str, Any]]:
    sheet, header_row, name_col, code_col = _best_real_header(workbook, "erp_articles")
    stack: list[str] = []
    result: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for row_number in range(header_row + 1, sheet.max_row + 1):
        raw_name = sheet.cell(row_number, name_col).value
        raw_code = sheet.cell(row_number, code_col).value

        if not _is_blank(raw_name):
            name = _hierarchy_text(raw_name)
            _set_stack(stack, _row_level(sheet, row_number, name_col, raw_name), name)

        if _is_blank(raw_code):
            continue

        code = str(raw_code).strip()
        if not code or normalize_header(code) == "код":
            continue
        if code in seen_codes:
            raise ValueError(f"ERP-справочник статей содержит повторяющийся код: {code}")
        if not stack:
            continue

        article = stack[-1]
        expense_type = stack[0] if len(stack) >= 2 else ""
        expense_group = stack[-2] if len(stack) >= 3 else ""
        result.append(
            {
                "code": code,
                "name": article,
                "expense_type": expense_type,
                "expense_group": expense_group,
                "source_article": article,
            }
        )
        seen_codes.add(code)

    return result


def _parse_real_organizations(workbook: Any) -> list[dict[str, Any]]:
    sheet, header_row, name_col, code_col = _best_real_header(workbook, "organizations")
    path_col = _find_optional_column(sheet, header_row, PATH_ALIASES)

    stack: list[str] = []
    coded_stack: dict[int, str] = {}
    raw_nodes: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for row_number in range(header_row + 1, sheet.max_row + 1):
        raw_name = sheet.cell(row_number, name_col).value
        raw_code = sheet.cell(row_number, code_col).value

        level = 0
        if not _is_blank(raw_name):
            name = _hierarchy_text(raw_name)
            level = _row_level(sheet, row_number, name_col, raw_name)
            _set_stack(stack, level, name)
        elif stack:
            name = stack[-1]
            level = max(len(stack) - 1, 0)
        else:
            continue

        if _is_blank(raw_code):
            continue
        code = str(raw_code).strip()
        if not code or normalize_header(code) == "код":
            continue
        if code in seen_codes:
            raise ValueError(f"Справочник организаций содержит повторяющийся код: {code}")

        explicit_path = ""
        if path_col is not None:
            explicit_path = _clean_scalar(sheet.cell(row_number, path_col).value)
        full_path = explicit_path or " → ".join(stack)

        parent_id = None
        for parent_level in range(level - 1, -1, -1):
            if parent_level in coded_stack:
                parent_id = coded_stack[parent_level]
                break

        raw_nodes.append(
            {
                "node_id": code,
                "code": code,
                "name": name,
                "parent_id": parent_id,
                "full_path": full_path,
            }
        )
        seen_codes.add(code)
        coded_stack[level] = code
        for deeper in [item for item in coded_stack if item > level]:
            del coded_stack[deeper]

    if path_col is not None:
        by_path = {node["full_path"]: node["node_id"] for node in raw_nodes}
        for node in raw_nodes:
            separator = " → " if " → " in node["full_path"] else None
            if separator:
                parent_path = node["full_path"].rsplit(separator, 1)[0]
                node["parent_id"] = by_path.get(parent_path)

    return raw_nodes


def _parse_real_scenarios(workbook: Any) -> list[dict[str, Any]]:
    sheet, header_row, name_col, code_col = _best_real_header(workbook, "scenarios")
    result: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, sheet.max_row + 1):
        raw_name = sheet.cell(row_number, name_col).value
        raw_code = sheet.cell(row_number, code_col).value
        if _is_blank(raw_name):
            continue
        name = str(raw_name).strip()
        scenario_header_aliases = {
            normalize_header(alias)
            for alias in REAL_EXPORT_HEADERS["scenarios"]["name"]
        }
        if not name or normalize_header(name) in scenario_header_aliases:
            continue
        code = "" if _is_blank(raw_code) else str(raw_code).strip()
        year_match = re.search(r"(?<!\d)(20\d{2}|21\d{2})(?!\d)", name)
        year = int(year_match.group(1)) if year_match else 0
        result.append(
            {
                "name": name,
                "year": str(year),
                "erp_code": code,
                "comment": "",
            }
        )
    return result


def _best_real_header(workbook: Any, kind: str) -> tuple[Any, int, int, int]:
    aliases = REAL_EXPORT_HEADERS[kind]
    candidates: list[tuple[int, Any, int, int, int]] = []
    for sheet in workbook.worksheets:
        for row_number in range(1, min(sheet.max_row, 100) + 1):
            normalized = {
                index: normalize_header(cell.value)
                for index, cell in enumerate(sheet[row_number], start=1)
            }
            name_matches = [
                index for index, value in normalized.items() if value in aliases["name"]
            ]
            code_matches = [
                index for index, value in normalized.items() if value in aliases["code"]
            ]
            if len(name_matches) != 1 or len(code_matches) != 1:
                continue
            name_col, code_col = name_matches[0], code_matches[0]
            score = sum(
                1
                for candidate_row in range(row_number + 1, sheet.max_row + 1)
                if not _is_blank(sheet.cell(candidate_row, code_col).value)
            )
            candidates.append((score, sheet, row_number, name_col, code_col))

    if not candidates:
        raise ValueError("Не найден заголовок известной ERP-выгрузки")
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, sheet, header_row, name_col, code_col = candidates[0]
    return sheet, header_row, name_col, code_col


def _find_optional_column(sheet: Any, header_row: int, aliases: set[str]) -> int | None:
    normalized_aliases = {normalize_header(alias) for alias in aliases}
    matches = [
        index
        for index, cell in enumerate(sheet[header_row], start=1)
        if normalize_header(cell.value) in normalized_aliases
    ]
    return matches[0] if len(matches) == 1 else None


def _row_level(sheet: Any, row_number: int, name_col: int, value: Any) -> int:
    cell = sheet.cell(row_number, name_col)
    indent = int(cell.alignment.indent or 0)
    outline = int(sheet.row_dimensions[row_number].outlineLevel or 0)
    text = str(value)
    leading = len(text) - len(text.lstrip(" \t"))
    leading_level = leading // 2
    return max(indent, outline, leading_level)


def _set_stack(stack: list[str], level: int, name: str) -> None:
    level = max(level, 0)
    if level > len(stack):
        level = len(stack)
    del stack[level:]
    stack.append(name)


def _hierarchy_text(value: Any) -> str:
    return str(value).lstrip(" \t\r\n")


def _match_headers(values: list[Any], required: dict[str, set[str]]) -> dict[str, int] | None:
    normalized = {index: normalize_header(value) for index, value in enumerate(values, start=1)}
    columns: dict[str, int] = {}
    for field, aliases in required.items():
        normalized_aliases = {normalize_header(alias) for alias in aliases}
        matches = [index for index, value in normalized.items() if value in normalized_aliases]
        if len(matches) != 1:
            return None
        columns[field] = matches[0]
    return columns


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _clean_scalar(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _clean_flat_value(field: str, value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if field in {"code", "node_id", "parent_id", "erp_code", "year", "comment"}:
        return text.strip()
    return text


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
