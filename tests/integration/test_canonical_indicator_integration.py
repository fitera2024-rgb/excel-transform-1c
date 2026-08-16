from __future__ import annotations

import pytest

from excel_transform_1c.application.service import WorkflowService
from excel_transform_1c.core.indicator_matching import INDICATOR_MATCHED
from excel_transform_1c.core.opiu_rules.opiu_rule_models import (
    AUTO_MATCH,
    NOT_FOUND,
    OPIURule,
    opiu_rule_to_payload,
)
from tests.helpers.workbooks import (
    BDR_FULL_INDICATORS,
    bdr_full_workbook_bytes,
    erp_organization_hierarchy_bytes,
)


pytestmark = pytest.mark.integration


def _rule(*, group: str, article: str, indicator: str) -> OPIURule:
    return OPIURule(
        rule_id=f"canonical-{group}-{article}",
        report_line="Расходы по основной деятельности",
        report_indicator=indicator,
        disclosure_group=group,
        article=article,
        article_code="",
        source="Точный источник ОПИУ ERP",
        formula_condition="",
        required_analytics=(),
        region_required=False,
        network_required=False,
        cfo_required=False,
        sales_channel="",
    )


def _process_bdr(tmp_path, rules: list[OPIURule]):
    service = WorkflowService(tmp_path / "runtime")
    service.upload_reference("organizations", erp_organization_hierarchy_bytes())
    service.store.save_opiu_rules([opiu_rule_to_payload(rule) for rule in rules])
    scenario = next(
        item for item in service.store.list_scenarios() if item.name == "ПЛАН 2026"
    )
    reporting_unit = "АЮ Административный Отдел"
    context = service.build_context(
        reporting_unit,
        "000000001",
        scenario.scenario_id,
        2026,
        [],
    )
    pending = service.prepare_upload(
        "БДР 2026 ИТОГ.xlsx",
        bdr_full_workbook_bytes(reporting_unit=reporting_unit),
        context,
    )
    run = service.process_upload(
        pending.upload_id,
        pending.candidates[0].candidate_id,
    )
    return service, run


def test_full_bdr_kpi_stays_direct_while_expense_uses_opiu_formula_rule(tmp_path):
    service, run = _process_bdr(
        tmp_path,
        [_rule(group="Связь", article="Интернет", indicator="Связь по формуле ОПИУ")],
    )

    kpi = next(record for record in run.records if record.source_article == "Оборот в кг")
    expense = next(record for record in run.records if record.source_article == "Интернет")

    assert kpi.indicator_match_status == INDICATOR_MATCHED
    assert kpi.indicator == "Оборот в кг"
    assert expense.indicator_match_status == AUTO_MATCH
    assert expense.indicator == "Связь по формуле ОПИУ"
    assert expense.sales_channel == ""

    diagnostics = service.bdr_diagnostics(run.run_id)
    assert diagnostics is not None
    assert diagnostics["kpi_exported"] == 6
    assert diagnostics["exported"] == len(BDR_FULL_INDICATORS) - 5 + 1


def test_formula_source_authority_overrides_conflicting_legacy_classifier(tmp_path):
    service = WorkflowService(tmp_path / "runtime")
    service.store.replace_reference(
        "article_indicators",
        [
            {
                "erp_code": "00-000069",
                "article_path": "Административные расходы → Связь → Интернет",
                "article_name": "Интернет",
                "indicator": "Legacy indicator",
                "sales_channel": "Legacy channel",
                "indicator_type": "EXPENSE",
            }
        ],
    )
    service.upload_reference("organizations", erp_organization_hierarchy_bytes())
    service.store.save_opiu_rules(
        [
            opiu_rule_to_payload(
                _rule(
                    group="Связь",
                    article="Интернет",
                    indicator="Formula/source indicator",
                )
            )
        ]
    )
    scenario = next(
        item for item in service.store.list_scenarios() if item.name == "ПЛАН 2026"
    )
    context = service.build_context(
        "АЮ Административный Отдел",
        "000000001",
        scenario.scenario_id,
        2026,
        [],
    )
    pending = service.prepare_upload(
        "БДР 2026 ИТОГ.xlsx",
        bdr_full_workbook_bytes(reporting_unit="АЮ Административный Отдел"),
        context,
    )
    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
    expense = next(record for record in run.records if record.source_article == "Интернет")

    assert expense.indicator_match_status == AUTO_MATCH
    assert expense.indicator == "Formula/source indicator"
    assert expense.sales_channel == ""


def test_formula_catalog_fails_closed_without_bypassing_to_direct_expense(tmp_path):
    service, run = _process_bdr(
        tmp_path,
        [_rule(group="Маркетинг", article="Реклама", indicator="Маркетинг")],
    )

    kpi = next(record for record in run.records if record.source_article == "Оборот в кг")
    expense = next(record for record in run.records if record.source_article == "Интернет")

    assert kpi.indicator_match_status == INDICATOR_MATCHED
    assert kpi.indicator == "Оборот в кг"
    assert expense.indicator_match_status == NOT_FOUND
    assert expense.indicator == ""
    assert "группа раскрытия" in expense.indicator_match_reason
    unresolved = service.indicator_unresolved_rows(run.run_id)
    assert any(item["source_article"] == "Интернет" for item in unresolved)

    diagnostics = service.bdr_diagnostics(run.run_id)
    assert diagnostics is not None
    assert diagnostics["exported"] == len(BDR_FULL_INDICATORS) - 5
    assert any(item["indicator"] == "Интернет" for item in diagnostics["exclusions"])
