from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook, load_workbook

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


def load_cached_workbook(path: str | Path):
    return load_workbook(path, data_only=True, read_only=True)


def detect_path(path: str | Path) -> list[CandidateRange]:
    workbook = load_cached_workbook(path)
    try:
        return detect_candidate_ranges(workbook)
    finally:
        workbook.close()


def read_path(path: str | Path, candidate: CandidateRange, source_file: str):
    workbook = load_cached_workbook(path)
    try:
        return read_source_rows(workbook, candidate, source_file)
    finally:
        workbook.close()


def export_opiu_light(records: list[PreviewRecord]) -> bytes:
    workbook = Workbook()
    try:
        sheet = workbook.active
        sheet.title = "OPIU Light"
        sheet.append(EXPORT_HEADERS)
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
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()
    finally:
        workbook.close()
