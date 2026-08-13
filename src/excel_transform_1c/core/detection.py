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


def detect_candidate_ranges(
    workbook: Any,
    scan_rows: int = 100,
    scan_columns: int = 100,
) -> list[CandidateRange]:
    raw: list[tuple[Any, int, dict[str, int]]] = []
    for sheet in workbook.worksheets:
        max_row = min(sheet.max_row or scan_rows, scan_rows)
        max_column = min(sheet.max_column or scan_columns, scan_columns)
        rows = sheet.iter_rows(
            min_row=1,
            max_row=max_row,
            min_col=1,
            max_col=max_column,
            values_only=True,
        )
        for row_number, values in enumerate(rows, start=1):
            schema = _column_schema(values)
            if schema:
                raw.append((sheet, row_number, schema))

    candidates: list[CandidateRange] = []
    for index, (sheet, header_row, columns) in enumerate(raw):
        later_headers = [
            other_row
            for other_sheet, other_row, _ in raw
            if other_sheet.title == sheet.title and other_row > header_row
        ]
        upper_bound = min(later_headers) - 1 if later_headers else sheet.max_row
        last_data_row = _last_data_row(sheet, header_row + 1, upper_bound, columns)
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


def _last_data_row(
    sheet: Any,
    first_row: int,
    upper_bound: int | None,
    columns: dict[str, int],
) -> int:
    relevant = list(columns.values())
    min_column = min(relevant)
    max_column = max(relevant)
    last = first_row - 1
    empty_streak = 0
    row_options = {
        "min_row": first_row,
        "min_col": min_column,
        "max_col": max_column,
        "values_only": True,
    }
    if upper_bound is not None:
        row_options["max_row"] = upper_bound
    rows = sheet.iter_rows(**row_options)
    for row_number, row in enumerate(rows, start=first_row):
        values = [row[column - min_column] for column in relevant]
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
    relevant = list(candidate.columns.values())
    min_column = min(relevant)
    max_column = max(relevant)
    rows = sheet.iter_rows(
        min_row=candidate.first_data_row,
        max_row=candidate.last_data_row,
        min_col=min_column,
        max_col=max_column,
        values_only=True,
    )
    for row_number, row in enumerate(rows, start=candidate.first_data_row):
        def value(field: str) -> Any:
            return row[candidate.columns[field] - min_column]

        month_values = tuple(
            value(f"month_{month}")
            for month in range(1, 13)
        )
        shared_values = {
            field: value(field)
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
