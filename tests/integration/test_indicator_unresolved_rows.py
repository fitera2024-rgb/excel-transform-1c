from decimal import Decimal

from excel_transform_1c.application.service import WorkflowService
from excel_transform_1c.core.indicator_matching import (
    INDICATOR_AMBIGUOUS,
    INDICATOR_INCOMPLETE,
    INDICATOR_MISSING,
)
from excel_transform_1c.core.models import (
    CandidateRange,
    IndicatorType,
    PreviewRecord,
    ProcessedRun,
    RunContext,
    SourcePointer,
)


def make_run(tmp_path, status: str, reason: str) -> tuple[WorkflowService, ProcessedRun]:
    service = WorkflowService(tmp_path)
    pointer = SourcePointer("source.xlsx", "Бюджет", 7, "H7", "source_article")
    record = PreviewRecord(
        record_id="r1",
        source_row=7,
        month=1,
        year=2026,
        reporting_unit="ООО ФИТЭРА",
        organization="ООО ФИТЭРА",
        scenario="Бюджет 2026",
        department="",
        organization_type="",
        cfo="",
        expense_type="Коммерческие расходы",
        expense_group="",
        source_article="Комиссия",
        erp_code="ERP-7",
        erp_article_name="Комиссия",
        tax="Не требуется",
        amount=Decimal("10"),
        pointers={"source_article": pointer},
        indicator_match_status=status,
        indicator_match_reason=reason,
    )
    run = ProcessedRun(
        run_id="run-1",
        context=RunContext(
            reporting_unit="ООО ФИТЭРА",
            organization_node_id="org",
            organization_name="ООО ФИТЭРА",
            scenario_id="scenario",
            scenario_name="Бюджет 2026",
            scenario_year=2026,
            scenario_erp_confirmed=True,
            year=2026,
        ),
        source_file="source.xlsx",
        candidate=CandidateRange("c", "Бюджет", 1, 2, 7, {}),
        records=[record],
        issues=[],
        created_at="2026-08-15T00:00:00+00:00",
    )
    service.runs[run.run_id] = run
    return service, run


def assert_business_row(tmp_path, status: str, expected_label: str):
    service, _ = make_run(tmp_path, status, "Понятная бизнес-причина")
    rows = service.indicator_unresolved_rows("run-1")
    assert len(rows) == 1
    assert rows[0]["source_line"] == "Бюджет!7"
    assert rows[0]["expense_group"] == "Без группы"
    assert rows[0]["erp_code"] == "ERP-7"
    assert rows[0]["status"] == expected_label
    assert rows[0]["reason"] == "Понятная бизнес-причина"
    assert rows[0]["action"] == "Загрузить / дополнить классификатор"
    assert "source_key" not in rows[0]
    assert "id" not in rows[0]


def test_missing_is_visible_as_business_row(tmp_path):
    assert_business_row(tmp_path, INDICATOR_MISSING, "Не найдено")


def test_ambiguous_is_visible_as_business_row(tmp_path):
    assert_business_row(tmp_path, INDICATOR_AMBIGUOUS, "Неоднозначно")


def test_incomplete_is_visible_as_business_row(tmp_path):
    assert_business_row(tmp_path, INDICATOR_INCOMPLETE, "Правило заполнено не полностью")


def test_missing_rule_declared_revenue_analytics_has_input_action(tmp_path):
    service, run = make_run(
        tmp_path,
        INDICATOR_INCOMPLETE,
        "Для дохода не заполнены поля точного правила: ИНТ канал сбыта",
    )
    run.records[0].indicator = "Выручка"
    run.records[0].indicator_type = IndicatorType.REVENUE

    revenue_row = service.indicator_unresolved_rows("run-1")[0]
    assert revenue_row["action"] == (
        "Проверить обязательные поля дохода во входном бюджете"
    )

    run.records[0].indicator_type = IndicatorType.EXPENSE
    expense_row = service.indicator_unresolved_rows("run-1")[0]
    assert expense_row["action"] == "Загрузить / дополнить классификатор"


def test_row_disappears_after_same_run_exact_rematch_without_read_path(tmp_path, monkeypatch):
    service, run = make_run(tmp_path, INDICATOR_MISSING, "Не найдено")
    run.records[0].erp_code = ""
    service.store.replace_reference(
        "article_indicators",
        [
            {
                "erp_code": "",
                "article_path": "Коммерческие расходы →  → Комиссия",
                "article_name": "Комиссия",
                "indicator": "Комиссии",
                "sales_channel": "Розница",
            }
        ],
    )
    monkeypatch.setattr(
        "excel_transform_1c.application.service.read_path",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("read_path called")),
    )
    service._apply_indicator_matches(run)
    assert service.indicator_unresolved_rows("run-1") == []
    assert run.rerun_count == 0
