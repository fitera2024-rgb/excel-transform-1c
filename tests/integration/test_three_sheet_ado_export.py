from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from excel_transform_1c.adapters.excel import (
    ADO_INDICATOR_HEADERS,
    ADO_OPIU_HEADERS,
    EXPORT_HEADERS,
    export_opiu_light,
)
from excel_transform_1c.core.models import PreviewRecord


pytestmark = pytest.mark.integration


def _record() -> PreviewRecord:
    return PreviewRecord(
        record_id="record-1",
        source_row=7,
        month=1,
        year=2026,
        reporting_unit="АЮ",
        organization="Организация 1",
        scenario="ПЛАН 2026",
        department="Подразделение 1",
        organization_type="ТК",
        cfo="ЦФО 1",
        expense_type="Административные расходы",
        expense_group="Хозяйственные расходы",
        source_article="Перчатки",
        erp_code="00-000169",
        erp_article_name="Перчатки",
        tax="БЕЗ НДС",
        amount=Decimal("123.45"),
    )


def test_export_keeps_legacy_sheet_and_adds_two_ado_sheets():
    payload = export_opiu_light([_record()])
    workbook = load_workbook(BytesIO(payload), data_only=True)
    try:
        assert workbook.sheetnames == ["OPIU Light", "ОПИУ", "Показатели"]

        legacy = workbook["OPIU Light"]
        assert tuple(cell.value for cell in legacy[1]) == EXPORT_HEADERS
        assert legacy.max_row == 2
        assert legacy["M2"].value == "00-000169"
        assert legacy["P2"].value == 123.45

        ado = workbook["ОПИУ"]
        assert tuple(cell.value for cell in ado[1]) == ADO_OPIU_HEADERS
        assert ado.max_row == 2
        assert tuple(cell.value for cell in ado[2]) == (
            "Организация 1",
            "ПЛАН 2026",
            2026,
            1,
            "01.2026",
            "Подразделение 1",
            None,
            "ЦФО 1",
            None,
            "Административные расходы",
            "00-000169",
            "Перчатки",
            None,
            None,
            None,
            None,
            123.45,
        )
        assert ado["K2"].data_type == "s"
        assert ado["K2"].number_format == "@"
        assert isinstance(ado["Q2"].value, (int, float))

        indicators = workbook["Показатели"]
        assert tuple(cell.value for cell in indicators[1]) == ADO_INDICATOR_HEADERS
        assert indicators.max_row == 1
    finally:
        workbook.close()


def test_ado_opiu_keeps_rows_when_reference_codes_are_missing():
    record = _record()
    record.erp_code = ""
    record.erp_article_name = ""

    payload = export_opiu_light([record])
    workbook = load_workbook(BytesIO(payload), data_only=True)
    try:
        ado = workbook["ОПИУ"]
        assert ado.max_row == 2
        assert ado["G2"].value is None
        assert ado["I2"].value is None
        assert ado["K2"].value is None
        assert ado["L2"].value == "Перчатки"
        assert ado["Q2"].value == 123.45
    finally:
        workbook.close()
