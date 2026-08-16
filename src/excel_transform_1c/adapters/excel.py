from __future__ import annotations

import re
import tempfile
import zipfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterator

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from excel_transform_1c.adapters.workbook_repair import prepare_workbook
from excel_transform_1c.core.detection import detect_candidate_ranges, read_source_rows
from excel_transform_1c.core.indicator_matching import (
    IndicatorExportRow,
    aggregate_indicator_rows,
)
from excel_transform_1c.core.models import CandidateRange, PreviewRecord


# Business export sheet. Reference names and codes intentionally use separate
# columns; a display path with a parenthesized code must never leak here.
EXPORT_HEADERS = (
    "Единица отчёта",
    "Организация",
    "Код организации",
    "Сценарий",
    "Год",
    "Месяц",
    "Период",
    "Департамент",
    "Вид организации",
    "Отдел",
    "ЦФО",
    "Код ЦФО",
    "Тип расходов",
    "Группа расходов",
    "Исходное название статьи",
    "ERP-код статьи",
    "Официальное название статьи ERP",
    "Налогообложение",
    "Сумма",
    "Статус",
    "Комментарий",
    "Номер исходной строки",
)

# ADO-oriented sheet requested by the owner. Missing reference codes remain
# empty until the corresponding catalogs are uploaded; business rows are not
# dropped because a code is not available yet.
ADO_OPIU_HEADERS = (
    "Организация",
    "Код организации",
    "Сценарий",
    "Год",
    "Месяц",
    "Период",
    "Департамент",
    "Отдел",
    "ЦФО",
    "Код ЦФО",
    "Тип расходов",
    "Код статьи",
    "Название статьи",
    "Инт Номенклатура",
    "Код номенклатуры",
    "Регион продаж",
    "Код региона продаж",
    "Сумма",
)

ADO_INDICATOR_HEADERS = (
    "Организация",
    "Код организации",
    "Сценарий",
    "Год",
    "Месяц",
    "Период",
    "Канал сбыта",
    "Тип расходов",
    "Сумма",
)


def _separate_organization_reference(value: str) -> tuple[str, str]:
    """Split the exact RunContext display contract into export name and code."""

    text = value.strip()
    match = re.fullmatch(r"(?P<path>.+) \((?P<code>[^()]*)\)", text)
    if match is None:
        path = text
        code = ""
    else:
        path = match.group("path").strip()
        code = match.group("code").strip()
    name = path.rsplit(" → ", 1)[-1].strip()
    return name, code


def _record_organization_reference(record: PreviewRecord) -> tuple[str, str]:
    """Prefer the exact root reference produced by the hierarchy resolver."""

    if record.organization_unit or record.organization_unit_code:
        return (
            record.organization_unit.strip(),
            record.organization_unit_code.strip(),
        )
    return _separate_organization_reference(record.organization)


def _indicator_organization_references(
    records: list[PreviewRecord],
) -> dict[str, tuple[str, str]]:
    """Resolve one exact root reference for every aggregated context value."""

    candidates: dict[str, set[tuple[str, str]]] = {}
    for record in records:
        if not (record.organization_unit or record.organization_unit_code):
            continue
        candidates.setdefault(record.organization, set()).add(
            _record_organization_reference(record)
        )

    resolved: dict[str, tuple[str, str]] = {}
    for organization, references in candidates.items():
        if len(references) != 1:
            raise ValueError(
                "Для одного контекста экспорта найдены разные exact ERP-организации"
            )
        resolved[organization] = next(iter(references))
    return resolved


@contextmanager
def load_cached_workbook(
    path: str | Path,
    *,
    read_only: bool = True,
) -> Iterator[object]:
    """Open cached values through a disposable OOXML compatibility copy when needed."""

    source_path = Path(path)
    # Keep the loader injectable for focused adapter tests that use a virtual
    # path. Real files are first staged into a separate validated/repaired
    # OOXML working copy; the original upload remains byte-for-byte unchanged.
    prepared_path = (
        prepare_workbook(source_path).working_path
        if source_path.exists()
        else source_path
    )
    workbook = None
    try:
        load_options = {"data_only": True, "read_only": read_only}
        if not read_only:
            load_options["keep_links"] = False
        workbook = load_workbook(prepared_path, **load_options)
        yield workbook
        return
    except KeyError as exc:
        if "sharedStrings.xml" not in str(exc):
            raise
    finally:
        if workbook is not None:
            workbook.close()

    with tempfile.TemporaryDirectory(prefix="excel_transform_1c_") as temp_dir:
        compatible = Path(temp_dir) / prepared_path.name
        _normalized_ooxml_copy(prepared_path, compatible)
        workbook = load_workbook(
            compatible,
            data_only=True,
            read_only=read_only,
            keep_links=False,
        )
        try:
            yield workbook
        finally:
            workbook.close()


def _normalized_ooxml_copy(source: Path, target: Path) -> None:
    with zipfile.ZipFile(source, "r") as archive, zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as output:
        for info in archive.infolist():
            name = info.filename
            data = archive.read(name)
            if name.lower() == "xl/sharedstrings.xml":
                name = "xl/sharedStrings.xml"
            if name.lower() == "[content_types].xml":
                text = data.decode("utf-8", errors="strict")
                text = re.sub(
                    r'PartName="/xl/SharedStrings\\.xml"',
                    'PartName="/xl/sharedStrings.xml"',
                    text,
                    flags=re.IGNORECASE,
                )
                data = text.encode("utf-8")
            output.writestr(name, data)


def detect_path(path: str | Path) -> list[CandidateRange]:
    with load_cached_workbook(path) as workbook:
        return detect_candidate_ranges(workbook)


def read_path(path: str | Path, candidate: CandidateRange, source_file: str):
    # Intalev hierarchy can be encoded in row outline levels.  Open only that
    # bounded workflow in normal mode because ReadOnlyWorksheet deliberately
    # omits row_dimensions; prepared-budget workbooks stay streaming/read-only.
    read_only = candidate.source_kind != "intalev_opiu"
    with load_cached_workbook(path, read_only=read_only) as workbook:
        return read_source_rows(workbook, candidate, source_file)


def _style_header(sheet, headers: tuple[str, ...], last_column: str) -> None:
    sheet.append(headers)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{last_column}1"
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_legacy_sheet(sheet, records: list[PreviewRecord]) -> None:
    sheet.title = "OPIU Light"
    _style_header(sheet, EXPORT_HEADERS, "V")
    for record in records:
        organization, organization_code = _record_organization_reference(record)
        department = record.department or None
        cfo = record.erp_department or record.cfo or None
        sheet.append(
            (
                record.reporting_unit,
                organization or None,
                organization_code or None,
                record.scenario,
                record.year,
                record.month,
                f"{record.month:02d}.{record.year}",
                department,
                record.organization_type,
                cfo,
                cfo,
                record.cfo_code or None,
                record.expense_type,
                record.expense_group,
                record.source_article,
                record.erp_code,
                record.erp_article_name,
                record.tax,
                float(record.amount) if record.amount is not None else None,
                record.status,
                record.comment,
                record.source_row,
            )
        )
    sheet.auto_filter.ref = f"A1:V{max(len(records) + 1, 1)}"
    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 28
    sheet.column_dimensions["C"].width = 18
    sheet.column_dimensions["D"].width = 18
    sheet.column_dimensions["G"].width = 12
    for column in ("H", "I", "J", "K", "M", "N", "O", "Q", "R", "T", "U"):
        sheet.column_dimensions[column].width = 22
    sheet.column_dimensions["L"].width = 16
    sheet.column_dimensions["P"].width = 18
    sheet.column_dimensions["S"].width = 16
    sheet.column_dimensions["V"].width = 18
    for column in ("C", "L", "P"):
        for cell in sheet[column]:
            cell.number_format = "@"
    sheet["S1"].alignment = Alignment(horizontal="center", vertical="center")
    for cell in sheet["S"][1:]:
        cell.number_format = '#,##0.00;[Red](#,##0.00);-'


def _write_ado_opiu_sheet(sheet, records: list[PreviewRecord]) -> None:
    sheet.title = "ОПИУ"
    _style_header(sheet, ADO_OPIU_HEADERS, "R")
    for record in records:
        organization, organization_code = _record_organization_reference(record)
        department = record.department or None
        cfo = record.erp_department or record.cfo or None
        sheet.append(
            (
                organization or None,
                organization_code or None,
                record.scenario,
                record.year,
                record.month,
                f"{record.month:02d}.{record.year}",
                department,
                cfo,
                cfo,
                record.cfo_code or None,
                record.expense_type,
                record.erp_code or None,
                record.erp_article_name or record.source_article,
                record.nomenclature or None,
                None,  # Код номенклатуры.
                record.sales_region or None,
                None,  # Код региона продаж.
                float(record.amount) if record.amount is not None else None,
            )
        )
    sheet.auto_filter.ref = f"A1:R{max(len(records) + 1, 1)}"
    widths = {
        "A": 28,
        "B": 20,
        "C": 18,
        "D": 10,
        "E": 10,
        "F": 12,
        "G": 28,
        "H": 28,
        "I": 28,
        "J": 16,
        "K": 24,
        "L": 18,
        "M": 30,
        "N": 24,
        "O": 18,
        "P": 20,
        "Q": 18,
        "R": 16,
    }
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    for column in ("B", "J", "L", "O", "Q"):
        for cell in sheet[column]:
            cell.number_format = "@"
    for cell in sheet["R"][1:]:
        cell.number_format = '#,##0.00;[Red](#,##0.00);-'


def _write_ado_indicators_sheet(
    sheet,
    rows: list[IndicatorExportRow],
    records: list[PreviewRecord],
) -> None:
    sheet.title = "Показатели"
    _style_header(sheet, ADO_INDICATOR_HEADERS, "I")
    organization_references = _indicator_organization_references(records)
    for row in rows:
        organization, organization_code = organization_references.get(
            row.organization,
            _separate_organization_reference(row.organization),
        )
        sheet.append(
            (
                organization or None,
                organization_code or None,
                row.scenario,
                row.year,
                row.month,
                row.period,
                row.sales_channel,
                row.indicator,
                float(row.amount),
            )
        )
    sheet.auto_filter.ref = f"A1:I{max(len(rows) + 1, 1)}"
    widths = {
        "A": 28,
        "B": 20,
        "C": 18,
        "D": 10,
        "E": 10,
        "F": 12,
        "G": 26,
        "H": 24,
        "I": 16,
    }
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    for cell in sheet["B"]:
        cell.number_format = "@"
    sheet["I1"].alignment = Alignment(horizontal="center", vertical="center")
    for cell in sheet["I"][1:]:
        cell.number_format = '#,##0.00;[Red](#,##0.00);-'


def export_opiu_light(records: list[PreviewRecord]) -> bytes:
    """Export the legacy sheet plus the two-sheet ADO schema in one workbook."""

    workbook = Workbook()
    try:
        legacy_sheet = workbook.active
        _write_legacy_sheet(legacy_sheet, records)
        _write_ado_opiu_sheet(workbook.create_sheet(), records)
        _write_ado_indicators_sheet(
            workbook.create_sheet(),
            aggregate_indicator_rows(records),
            records,
        )

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()
    finally:
        workbook.close()
