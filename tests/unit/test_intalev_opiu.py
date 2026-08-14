from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from excel_transform_1c.core.detection import detect_candidate_ranges, read_source_rows
from excel_transform_1c.core.models import ERPArticle, RunContext, STATUS_ATTENTION, STATUS_SKIPPED
from excel_transform_1c.core.transform import ExactERPMapper, transform_rows
from tests.helpers.workbooks import intalev_opiu_bytes


def _context() -> RunContext:
    return RunContext(
        "ПС",
        "ps",
        "Группа → ПС",
        "fact",
        "Факт",
        2025,
        True,
        2025,
    )


def _articles() -> list[ERPArticle]:
    return [
        ERPArticle("ERP-001", "Интернет ERP", "Административные расходы", "Связь", "Интернет"),
        ERPArticle("ERP-002", "Телефония ERP", "Административные расходы", "Связь", "Телефония"),
        ERPArticle("ERP-003", "Реклама ERP", "Административные расходы", "Маркетинг", "Реклама"),
    ]


def _rows(*, sheet_name: str = "TDSheet", monthly_error: bool = False):
    workbook = load_workbook(
        BytesIO(intalev_opiu_bytes(sheet_name=sheet_name, monthly_error=monthly_error)),
        data_only=True,
    )
    candidate = detect_candidate_ranges(workbook)[0]
    return workbook, candidate, read_source_rows(workbook, candidate, "synthetic-intalev.xlsx")


def test_structural_candidate_and_period_detection_ignore_sheet_name():
    workbook, candidate, rows = _rows(sheet_name="Совсем другое имя")
    try:
        assert candidate.sheet == "Совсем другое имя"
        assert candidate.source_kind == "intalev_opiu"
        assert candidate.header_row == 4
        assert candidate.first_data_row == 7
        assert candidate.last_data_row == 14
        assert candidate.source_year == 2025
        assert [candidate.columns[f"month_{month}"] for month in range(1, 13)] == list(
            range(5, 17)
        )
        assert len(rows) == 3
    finally:
        workbook.close()


def test_hierarchy_parsing_extracts_source_cfo_and_excludes_technical_totals():
    workbook, candidate, rows = _rows()
    try:
        assert candidate.source_cfo == "ЦД/ЦЗ Фонд развития"
        assert [(row.expense_type, row.expense_group, row.article) for row in rows] == [
            ("Административные расходы", "Связь", "Интернет"),
            ("Административные расходы", "Связь", "Телефония"),
            ("Административные расходы", "Маркетинг", "Реклама"),
        ]
        assert all(row.cfo == "ЦД/ЦЗ Фонд развития" for row in rows)
        assert not {"Расходы по основной деятельности ИТОГО", "EBITDA"}.intersection(
            row.article for row in rows
        )
    finally:
        workbook.close()


def test_maximum_completeness_preserves_zero_negative_and_monthly_error():
    workbook, _, rows = _rows(monthly_error=True)
    try:
        records, issues = transform_rows(rows, _context(), ExactERPMapper(_articles()))
    finally:
        workbook.close()

    assert len(records) == 36
    negative = next(record for record in records if record.amount == Decimal("-10"))
    assert negative.status == STATUS_ATTENTION
    assert "Отрицательная сумма" in negative.comment
    assert len([record for record in records if record.amount == Decimal("0")]) == 34
    skipped = next(record for record in records if record.source_row == 10 and record.month == 5)
    assert skipped.status == STATUS_SKIPPED
    assert skipped.amount is None
    assert "I10" in skipped.comment
    assert any(issue.kind == "monthly-error" and issue.pointer.cell == "I10" for issue in issues)
