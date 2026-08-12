from __future__ import annotations

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


def parse_reference_workbook(content: bytes, kind: str) -> list[dict[str, Any]]:
    workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
    required = {"erp_articles": ERP_HEADERS, "organizations": ORG_HEADERS, "scenarios": SCENARIO_HEADERS}[kind]
    candidates: list[tuple[Any, int, dict[str, int]]] = []
    for sheet in workbook.worksheets:
        for row_number in range(1, min(sheet.max_row, 50) + 1):
            values = [cell.value for cell in sheet[row_number]]
            columns = _match_headers(values, required)
            if columns:
                candidates.append((sheet, row_number, columns))
    if len(candidates) != 1:
        raise ValueError("Справочник должен содержать ровно один структурно распознаваемый диапазон")
    sheet, header_row, columns = candidates[0]
    rows: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, sheet.max_row + 1):
        item = {field: sheet.cell(row_number, column).value for field, column in columns.items()}
        if all(value is None for value in item.values()):
            continue
        rows.append({field: "" if value is None else str(value) for field, value in item.items()})
    return rows


def _match_headers(values: list[Any], required: dict[str, set[str]]) -> dict[str, int] | None:
    normalized = {index: normalize_header(value) for index, value in enumerate(values, start=1)}
    columns: dict[str, int] = {}
    for field, aliases in required.items():
        matches = [index for index, value in normalized.items() if value in {normalize_header(alias) for alias in aliases}]
        if len(matches) != 1:
            return None
        columns[field] = matches[0]
    return columns


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
