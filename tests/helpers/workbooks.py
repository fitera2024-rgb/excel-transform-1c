from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook
from openpyxl.styles import Alignment


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
            cfo_error,
            missing_mapping,
            negative,
            reporting_unit,
        )
        if two_candidates:
            second = workbook.create_sheet("Второй диапазон")
            _append_candidate(second, False, False, False, False, False, "ПС")
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _append_candidate(
    sheet,
    monthly_error: bool,
    shared_error: bool,
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
            "Департамент 1",
            "ТК",
            "ЦФО 1",
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
            "" if cfo_error else "ЦФО 2",
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
        sheet.append(["Код", "Официальное наименование", "Тип расходов", "Группа расходов", "Исходная статья"])
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


def realistic_reference_bytes(kind: str) -> bytes:
    """Synthetic workbooks that reproduce the documented ERP export structures."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Лист_1"
    for _ in range(6):
        sheet.append(["Синтетическая служебная строка"])

    if kind == "erp_articles":
        headers = [""] * 15
        headers[0] = "Статья доходов и расходов"
        headers[14] = "Код"
        sheet.append(headers)
        _append_hierarchy_name(sheet, "Административные", 0)
        _append_hierarchy_name(sheet, "Связь", 1)
        _append_hierarchy_name(sheet, "Интернет", 2)
        _append_code_row(sheet, 15, "ERP-001")
        _append_hierarchy_name(sheet, "Прочие", 1)
        _append_hierarchy_name(sheet, "!!!Удалить", 2)
        _append_code_row(sheet, 15, "ERP-DEL")
    elif kind == "organizations":
        headers = [""] * 39
        headers[0] = "Организации"
        headers[14] = "Код"
        headers[15] = "Родитель"
        headers[16] = "Полный путь"
        sheet.append(headers)
        _append_organization_export_row(sheet, "Группа", "ORG-1", "", "Группа", 0)
        _append_organization_export_row(sheet, "ПС", "ORG-2", "ORG-1", "Группа → ПС", 1)
        _append_organization_export_row(
            sheet,
            "!!!Удалить",
            "ORG-3",
            "ORG-2",
            "Группа → ПС → !!!Удалить",
            2,
        )
    elif kind == "scenarios":
        headers = [""] * 19
        headers[0] = "Сценарии"
        headers[18] = "Код"
        sheet.append(headers)
        row = [""] * 19
        row[0], row[18] = "ПЛАН_2026", "00010"
        sheet.append(row)
        row = [""] * 19
        row[0], row[18] = "Факт", "00001"
        sheet.append(row)
    else:
        raise ValueError(kind)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _append_hierarchy_name(sheet, name: str, indent: int) -> None:
    sheet.append([name])
    sheet.cell(sheet.max_row, 1).alignment = Alignment(indent=indent)


def _append_code_row(sheet, code_column: int, code: str) -> None:
    row = [""] * code_column
    row[code_column - 1] = code
    sheet.append(row)


def _append_organization_export_row(
    sheet,
    name: str,
    code: str,
    parent: str,
    full_path: str,
    indent: int,
) -> None:
    row = [""] * 39
    row[0], row[14], row[15], row[16] = name, code, parent, full_path
    sheet.append(row)
    sheet.cell(sheet.max_row, 1).alignment = Alignment(indent=indent)


def write_cached_formula_fixture(path: Path) -> None:
    path.write_bytes(workbook_bytes())
    with ZipFile(path, "r") as source:
        members = {name: source.read(name) for name in source.namelist()}
    sheet_name = "xl/worksheets/sheet1.xml"
    xml = members[sheet_name].decode("utf-8")
    xml = xml.replace('<c r="I3" t="n"><v>100</v></c>', '<c r="I3"><f>50+50</f><v>100</v></c>')
    members[sheet_name] = xml.encode("utf-8")
    with ZipFile(path, "w", ZIP_DEFLATED) as target:
        for name, data in members.items():
            target.writestr(name, data)
