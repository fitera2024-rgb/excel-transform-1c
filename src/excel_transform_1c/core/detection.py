from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from openpyxl.utils import get_column_letter

from .models import CandidateRange, MONTH_NAMES, SourceRow


BUSINESS_ALIASES: dict[str, set[str]] = {
    "reporting_unit": {"подразделение (цфо 1)", "единица отчета", "единица отчёта"},
    "expense_type": {"тип расходов"},
    "department": {"департамент (цфо 2)", "департамент"},
    "organization_type": {"вид организации"},
    "cfo": {"отдел", "цфо", "отдел / цфо"},
    "tax": {"налогообложение", "налог"},
    "expense_group": {"группа расходов", "группа"},
    "article": {"статья", "исходная статья"},
}

MONTH_ALIASES: dict[int, set[str]] = {
    1: {"январь", "янв", "01"},
    2: {"февраль", "фев", "02"},
    3: {"март", "мар", "03"},
    4: {"апрель", "апр", "04"},
    5: {"май", "05"},
    6: {"июнь", "июн", "06"},
    7: {"июль", "июл", "07"},
    8: {"август", "авг", "08"},
    9: {"сентябрь", "сен", "09"},
    10: {"октябрь", "окт", "10"},
    11: {"ноябрь", "ноя", "11"},
    12: {"декабрь", "дек", "12"},
}


def normalize_header(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("ё", "е").strip().casefold()
    return re.sub(r"\s+", " ", text)


def _column_schema(values: Iterable[Any]) -> dict[str, int] | None:
    headers = {index: normalize_header(value) for index, value in enumerate(values, start=1)}
    columns: dict[str, int] = {}
    for field, aliases in BUSINESS_ALIASES.items():
        normalized_aliases = {normalize_header(alias) for alias in aliases}
        matches = [index for index, value in headers.items() if value in normalized_aliases]
        if len(matches) != 1:
            return None
        columns[field] = matches[0]
    for month, aliases in MONTH_ALIASES.items():
        normalized_aliases = {normalize_header(alias) for alias in aliases}
        matches = [index for index, value in headers.items() if value in normalized_aliases]
        if len(matches) != 1:
            return None
        columns[f"month_{month}"] = matches[0]
    return columns


def detect_candidate_ranges(workbook: Any, scan_rows: int = 100) -> list[CandidateRange]:
    raw: list[tuple[Any, int, dict[str, int]]] = []
    for sheet in workbook.worksheets:
        max_row = min(sheet.max_row, scan_rows)
        for row_number in range(1, max_row + 1):
            schema = _column_schema(cell.value for cell in sheet[row_number])
            if schema:
                raw.append((sheet, row_number, schema))

    candidates: list[CandidateRange] = []
    for index, (sheet, header_row, columns) in enumerate(raw):
        next_header = next(
            (
                other_row
                for other_sheet, other_row, _ in raw
                if other_sheet.title == sheet.title and other_row > header_row
            ),
            sheet.max_row + 1,
        )
        last_data_row = _last_data_row(sheet, header_row + 1, next_header - 1, columns)
        if last_data_row < header_row + 1:
            continue
        candidates.append(
            CandidateRange(
                candidate_id=f"candidate-{index + 1}",
                sheet=sheet.title,
                header_row=header_row,
                first_data_row=header_row + 1,
                last_data_row=last_data_row,
                columns=columns,
            )
        )
    return candidates


def _last_data_row(sheet: Any, first_row: int, upper_bound: int, columns: dict[str, int]) -> int:
    relevant = list(columns.values())
    last = first_row - 1
    empty_streak = 0
    for row_number in range(first_row, upper_bound + 1):
        values = [sheet.cell(row_number, column).value for column in relevant]
        if all(value is None for value in values):
            empty_streak += 1
            if empty_streak >= 3:
                break
            continue
        empty_streak = 0
        last = row_number
    return last


def read_source_rows(workbook: Any, candidate: CandidateRange, source_file: str) -> list[SourceRow]:
    sheet = workbook[candidate.sheet]
    result: list[SourceRow] = []
    for row_number in range(candidate.first_data_row, candidate.last_data_row + 1):
        month_values = tuple(
            sheet.cell(row_number, candidate.columns[f"month_{month}"]).value
            for month in range(1, 13)
        )
        shared_values = {
            field: sheet.cell(row_number, candidate.columns[field]).value
            for field in BUSINESS_ALIASES
        }
        if all(value is None for value in (*shared_values.values(), *month_values)):
            continue
        cells = {
            field: f"{get_column_letter(column)}{row_number}"
            for field, column in candidate.columns.items()
        }
        result.append(
            SourceRow(
                source_file=source_file,
                sheet=candidate.sheet,
                row_number=row_number,
                months=month_values,
                cells=cells,
                **shared_values,
            )
        )
    return result
