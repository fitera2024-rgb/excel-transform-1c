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
from excel_transform_1c.core.models import CandidateRange, PreviewRecord


EXPORT_HEADERS = (
    "Единица отчёта",
    "Организация",
    "Сценарий",
    "Год",
    "Месяц",
    "Период",
    "Департамент",
    "Вид организации",
    "Отдел / ЦФО",
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
                    r'PartName="/xl/SharedStrings\.xml"',
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


def export_opiu_light(records: list[PreviewRecord]) -> bytes:
    workbook = Workbook()
    try:
        sheet = workbook.active
        sheet.title = "OPIU Light"
        sheet.append(EXPORT_HEADERS)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:S{max(len(records) + 1, 1)}"
        header_fill = PatternFill("solid", fgColor="1F4E78")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for record in records:
            sheet.append(
                (
                    record.reporting_unit,
                    record.organization,
                    record.scenario,
                    record.year,
                    record.month,
                    f"{record.month:02d}.{record.year}",
                    record.department,
                    record.organization_type,
                    record.cfo,
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
        sheet.column_dimensions["A"].width = 18
        sheet.column_dimensions["B"].width = 28
        sheet.column_dimensions["C"].width = 18
        sheet.column_dimensions["F"].width = 12
        for column in ("G", "H", "I", "J", "K", "L", "N", "O", "Q", "R"):
            sheet.column_dimensions[column].width = 22
        sheet.column_dimensions["M"].width = 18
        sheet.column_dimensions["P"].width = 16
        sheet.column_dimensions["S"].width = 18
        sheet["P1"].alignment = Alignment(horizontal="center", vertical="center")
        for cell in sheet["P"][1:]:
            cell.number_format = '#,##0.00;[Red](#,##0.00);-'
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()
    finally:
        workbook.close()
