from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
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

INTALEV_INDICATOR_ALIASES = {"показатели", "показатель"}
INTALEV_METADATA_CFO = re.compile(r"(?im)^\s*цфо\s*:\s*(.+?)\s*$")
INTALEV_PERIOD = re.compile(
    r"^\s*(\d{2})\.(\d{2})\.(\d{4})\s*-\s*"
    r"(\d{2})\.(\d{2})\.(\d{4})\s*$"
)
TECHNICAL_TOTAL = re.compile(r"(?:^|\s)итого(?:\s|$)", re.IGNORECASE)


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
    raw: list[tuple[Any, int, dict[str, int], str, str, int | None]] = []
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
                raw.append((sheet, row_number, schema, "prepared_budget", "", None))
                continue
            intalev = _intalev_schema(values)
            if intalev:
                source_cfo = _metadata_cfo(sheet, row_number)
                source_year = _period_year(values, intalev)
                raw.append(
                    (
                        sheet,
                        row_number,
                        intalev,
                        "intalev_opiu",
                        source_cfo,
                        source_year,
                    )
                )

    candidates: list[CandidateRange] = []
    for index, (sheet, header_row, columns, source_kind, source_cfo, source_year) in enumerate(raw):
        later_headers = [
            other_row
            for other_sheet, other_row, *_ in raw
            if other_sheet.title == sheet.title and other_row > header_row
        ]
        upper_bound = min(later_headers) - 1 if later_headers else sheet.max_row
        if source_kind == "intalev_opiu":
            first_data_row = _first_intalev_data_row(
                sheet, header_row + 1, upper_bound, columns["article"]
            )
            last_data_row = _last_intalev_data_row(
                sheet, first_data_row, upper_bound, columns["article"]
            )
        else:
            first_data_row = header_row + 1
            last_data_row = _last_data_row(sheet, first_data_row, upper_bound, columns)
        if last_data_row < first_data_row:
            continue
        candidates.append(
            CandidateRange(
                candidate_id=f"candidate-{index + 1}",
                sheet=sheet.title,
                header_row=header_row,
                first_data_row=first_data_row,
                last_data_row=last_data_row,
                columns=columns,
                source_kind=source_kind,
                source_cfo=source_cfo,
                source_year=source_year,
            )
        )
    return candidates


def _intalev_schema(values: Iterable[Any]) -> dict[str, int] | None:
    row = list(values)
    indicators = [
        index
        for index, value in enumerate(row, start=1)
        if normalize_header(value) in INTALEV_INDICATOR_ALIASES
    ]
    if len(indicators) != 1:
        return None

    months: dict[int, int] = {}
    years: set[int] = set()
    for index, value in enumerate(row, start=1):
        period = _parse_period(value)
        if period is None:
            continue
        year, month = period
        if month in months:
            return None
        months[month] = index
        years.add(year)
    if set(months) != set(range(1, 13)) or len(years) != 1:
        return None
    return {
        "article": indicators[0],
        **{f"month_{month}": months[month] for month in range(1, 13)},
    }


def _parse_period(value: Any) -> tuple[int, int] | None:
    if isinstance(value, datetime):
        return value.year, value.month
    if isinstance(value, date):
        return value.year, value.month
    match = INTALEV_PERIOD.match(str(value or ""))
    if not match:
        return None
    start_day, start_month, start_year, _, end_month, end_year = map(int, match.groups())
    if start_day != 1 or start_month != end_month or start_year != end_year:
        return None
    return start_year, start_month


def _period_year(values: Iterable[Any], columns: dict[str, int]) -> int | None:
    row = list(values)
    period = _parse_period(row[columns["month_1"] - 1])
    return period[0] if period else None


def _metadata_cfo(sheet: Any, header_row: int) -> str:
    for row in sheet.iter_rows(
        min_row=1,
        max_row=max(header_row - 1, 1),
        min_col=1,
        max_col=min(sheet.max_column or 1, 16),
        values_only=True,
    ):
        for value in row:
            match = INTALEV_METADATA_CFO.search(str(value or ""))
            if match:
                return match.group(1).strip()
    return ""


def _first_intalev_data_row(
    sheet: Any, first_row: int, upper_bound: int | None, label_column: int
) -> int:
    last_row = upper_bound if upper_bound is not None else sheet.max_row
    for row_number in range(first_row, last_row + 1):
        if normalize_header(sheet.cell(row_number, label_column).value):
            return row_number
    return last_row + 1


def _last_intalev_data_row(
    sheet: Any, first_row: int, upper_bound: int | None, label_column: int
) -> int:
    last_row = upper_bound if upper_bound is not None else sheet.max_row
    for row_number in range(last_row, first_row - 1, -1):
        if normalize_header(sheet.cell(row_number, label_column).value):
            return row_number
    return first_row - 1


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
    if candidate.source_kind == "intalev_opiu":
        return _read_intalev_source_rows(workbook, candidate, source_file)

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


def _read_intalev_source_rows(
    workbook: Any, candidate: CandidateRange, source_file: str
) -> list[SourceRow]:
    sheet = workbook[candidate.sheet]
    label_column = candidate.columns["article"]
    labelled: list[tuple[int, str, int]] = []
    for row_number in range(candidate.first_data_row, candidate.last_data_row + 1):
        cell = sheet.cell(row_number, label_column)
        name = str(cell.value or "").strip()
        if not name:
            continue
        indent = int(cell.alignment.indent or 0)
        outline = int(sheet.row_dimensions[row_number].outlineLevel or 0)
        level = indent if indent else outline * 2
        labelled.append((row_number, name, level))

    stack: dict[int, str] = {}
    result: list[SourceRow] = []
    for index, (row_number, name, level) in enumerate(labelled):
        stack[level] = name
        for stale_level in [item for item in stack if item > level]:
            del stack[stale_level]

        next_level = labelled[index + 1][2] if index + 1 < len(labelled) else -1
        is_leaf = next_level <= level
        if not is_leaf or level == 0 or TECHNICAL_TOTAL.search(name):
            continue

        business_ancestors = [
            stack[item]
            for item in sorted(stack)
            if 0 < item < level and not TECHNICAL_TOTAL.search(stack[item])
        ]
        expense_type = business_ancestors[0] if business_ancestors else ""
        expense_group = business_ancestors[-1] if business_ancestors else ""
        if normalize_header(expense_group) == "<пустое значение>":
            expense_group = ""

        month_values = tuple(
            0
            if sheet.cell(row_number, candidate.columns[f"month_{month}"]).value in (None, "")
            else sheet.cell(row_number, candidate.columns[f"month_{month}"]).value
            for month in range(1, 13)
        )
        article_cell = f"{get_column_letter(label_column)}{row_number}"
        metadata_cell = "A2"
        cells = {
            "reporting_unit": metadata_cell,
            "expense_type": article_cell,
            "department": article_cell,
            "organization_type": article_cell,
            "cfo": metadata_cell,
            "tax": article_cell,
            "expense_group": article_cell,
            "article": article_cell,
            **{
                f"month_{month}": (
                    f"{get_column_letter(candidate.columns[f'month_{month}'])}{row_number}"
                )
                for month in range(1, 13)
            },
        }
        result.append(
            SourceRow(
                source_file=source_file,
                sheet=candidate.sheet,
                row_number=row_number,
                reporting_unit=None,
                expense_type=expense_type,
                department=None,
                organization_type=None,
                cfo=candidate.source_cfo,
                tax=None,
                expense_group=expense_group,
                article=name,
                months=month_values,
                cells=cells,
            )
        )
    return result
