from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook
from openpyxl.styles import Alignment
from msoffcrypto.format.ooxml import OOXMLFile


HEADERS = [
    "ПОДРАЗДЕЛЕНИЕ (ЦФО 1)",
    "ТИП РАСХОДОВ",
    "ДЕПАРТАМЕНТ (ЦФО 2)",
    "Вид организации",
    "ОТДЕЛ",
    "НАЛОГООБЛОЖЕНИЕ",
    "ГРУППА РАСХОДОВ",
    "СТАТЬЯ",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def workbook_bytes(
    *,
    sheet_name: str = "Произвольное имя",
    two_candidates: bool = False,
    no_range: bool = False,
    monthly_error: bool = False,
    shared_error: bool = False,
    department_error: bool = False,
    cfo_error: bool = False,
    missing_mapping: bool = False,
    negative: bool = False,
    reporting_unit: str = "ПС",
) -> bytes:
    workbook = Workbook()
    first = workbook.active
    first.title = sheet_name
    if no_range:
        first.append(["Это не загрузочный диапазон", "Значение"])
        first.append(["x", 1])
    else:
        _append_candidate(
            first,
            monthly_error,
            shared_error,
            department_error,
            cfo_error,
            missing_mapping,
            negative,
            reporting_unit,
        )
        if two_candidates:
            second = workbook.create_sheet("Второй диапазон")
            _append_candidate(second, False, False, False, False, False, False, reporting_unit)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def large_workbook_bytes(
    inert_rows: int = 25_000,
    inert_columns: int = 8,
) -> bytes:
    """Build a multi-MiB XLSX with only two processable business rows."""

    workbook = Workbook(write_only=True)
    business = workbook.create_sheet("Небольшой business range")
    _append_candidate(business, False, False, False, False, False, False, "ПС")

    inert = workbook.create_sheet("Большой inert synthetic лист")
    for row in range(inert_rows):
        values = []
        for column in range(inert_columns):
            digest = hashlib.blake2s(
                f"inert:{row}:{column}".encode(),
                digest_size=18,
            ).digest()
            values.append(base64.urlsafe_b64encode(digest).decode("ascii"))
        inert.append(values)
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def protected_workbook_bytes(content: bytes, password: str) -> bytes:
    output = BytesIO()
    OOXMLFile(BytesIO(content)).encrypt(password, output)
    return output.getvalue()


def _append_candidate(
    sheet,
    monthly_error: bool,
    shared_error: bool,
    department_error: bool,
    cfo_error: bool,
    missing_mapping: bool,
    negative: bool,
    reporting_unit: str,
) -> None:
    sheet.append(["Синтетический fixture: вымышленные данные"])
    sheet.append(HEADERS)
    months_a = [0] * 12
    months_a[0] = -10 if negative else 100
    if monthly_error:
        months_a[4] = "#REF!"
    sheet.append(
        [
            reporting_unit,
            "Административные",
            "" if department_error else "Департамент 1",
            "ТК",
            "" if cfo_error else "ЦФО 1",
            0.2,
            "Связь",
            "Интернет" if not missing_mapping else "Нет в ERP",
            *months_a,
        ]
    )
    sheet.append(
        [
            reporting_unit,
            "Коммерческие",
            "" if shared_error else "Департамент 2",
            "ТК",
            "ЦФО 2",
            "БЕЗ НДС",
            "Маркетинг",
            "Реклама",
            *([0] * 12),
        ]
    )


def reference_bytes(kind: str) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic"
    if kind == "erp_articles":
        sheet.append(
            [
                "Код",
                "Официальное наименование",
                "Тип расходов",
                "Группа расходов",
                "Исходная статья",
            ]
        )
        sheet.append(["ERP-001", "Интернет ERP", "Административные", "Связь", "Интернет"])
        sheet.append(["ERP-002", "Реклама ERP", "Коммерческие", "Маркетинг", "Реклама"])
        sheet.append(["ERP-DEL", "Удалить (видимая запись)", "Административные", "Прочие", "Удалить"])
    elif kind == "organizations":
        sheet.append(["ID", "Код", "Наименование", "Родитель ID", "Полный путь"])
        sheet.append(["root", "ORG-1", "Группа", "", "Группа"])
        sheet.append(["ps", "ORG-2", "ПС", "root", "Группа → ПС"])
        sheet.append(["cfo", "ORG-3", "ЦФО 1", "ps", "Группа → ПС → ЦФО 1"])
        sheet.append(["del", "ORG-4", "!!!Удалить", "ps", "Группа → ПС → !!!Удалить"])
        sheet.append(["other", "ORG-5", "Сосед", "root", "Группа → Сосед"])
    elif kind == "scenarios":
        sheet.append(["Наименование", "Год", "ERP-код", "Комментарий"])
        sheet.append(["ПЛАН_2026", 2026, "00010", "synthetic"])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def real_reference_bytes(kind: str) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Лист_1"

    if kind == "erp_articles":
        sheet.cell(1, 1, "Статья доходов и расходов")
        sheet.cell(1, 15, "Код")
        _hierarchy_cell(sheet, 2, "Административные", 0)
        _hierarchy_cell(sheet, 3, "Связь", 2)
        _hierarchy_cell(sheet, 4, "Интернет", 4)
        sheet.cell(5, 15, "ERP-001")
        _hierarchy_cell(sheet, 6, "Коммерческие", 0)
        _hierarchy_cell(sheet, 7, "Маркетинг", 2)
        _hierarchy_cell(sheet, 8, "Реклама", 4)
        sheet.cell(9, 15, "ERP-002")
        _hierarchy_cell(sheet, 10, "!!!Удалить", 0)
        _hierarchy_cell(sheet, 11, "Прочие", 2)
        _hierarchy_cell(sheet, 12, "Удалить", 4)
        sheet.cell(13, 15, "ERP-DEL")
    elif kind == "organizations":
        sheet.cell(1, 1, "Организации")
        sheet.cell(1, 39, "Код")
        rows = [
            (2, "Группа", "ORG-1", 0),
            (3, "ПС", "ORG-2", 1),
            (4, "ЦФО 1", "ORG-3", 2),
            (5, "!!!Удалить", "ORG-4", 2),
            (6, "Сосед", "ORG-5", 1),
        ]
        for row, name, code, level in rows:
            _hierarchy_cell(sheet, row, name, level)
            sheet.cell(row, 39, code)
    elif kind == "scenarios":
        sheet.cell(7, 1, "Сценарии")
        sheet.cell(7, 19, "Код")
        sheet.cell(8, 1, "ПЛАН 2026")
        sheet.cell(8, 19, "00010")
        sheet.cell(9, 1, "Факт")
        sheet.cell(9, 19, "00001")

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _hierarchy_cell(sheet, row: int, value: str, level: int) -> None:
    cell = sheet.cell(row, 1, value)
    cell.alignment = Alignment(indent=level)


def write_cached_formula_fixture(path: Path) -> None:
    path.write_bytes(workbook_bytes())
    with ZipFile(path, "r") as source:
        members = {name: source.read(name) for name in source.namelist()}
    sheet_name = "xl/worksheets/sheet1.xml"
    xml = members[sheet_name].decode("utf-8")
    xml = xml.replace(
        '<c r="I3" t="n"><v>100</v></c>',
        '<c r="I3"><f>50+50</f><v>100</v></c>',
    )
    members[sheet_name] = xml.encode("utf-8")
    with ZipFile(path, "w", ZIP_DEFLATED) as target:
        for name, data in members.items():
            target.writestr(name, data)
