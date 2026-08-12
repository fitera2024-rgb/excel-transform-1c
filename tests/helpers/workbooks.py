from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook


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
    missing_mapping: bool = False,
    negative: bool = False,
) -> bytes:
    workbook = Workbook()
    first = workbook.active
    first.title = sheet_name
    if no_range:
        first.append(["Это не загрузочный диапазон", "Значение"])
        first.append(["x", 1])
    else:
        _append_candidate(first, monthly_error, shared_error, missing_mapping, negative)
        if two_candidates:
            second = workbook.create_sheet("Второй диапазон")
            _append_candidate(second, False, False, False, False)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _append_candidate(sheet, monthly_error: bool, shared_error: bool, missing_mapping: bool, negative: bool) -> None:
    sheet.append(["Синтетический fixture: вымышленные данные"])
    sheet.append(HEADERS)
    months_a = [0] * 12
    months_a[0] = -10 if negative else 100
    if monthly_error:
        months_a[4] = "#REF!"
    sheet.append(
        [
            "ПС",
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
            "ПС",
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
