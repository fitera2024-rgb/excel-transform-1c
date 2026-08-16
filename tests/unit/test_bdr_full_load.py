from io import BytesIO

from openpyxl import load_workbook

from excel_transform_1c.adapters.references import (
    organization_nodes,
    parse_reference_workbook,
)
from excel_transform_1c.application.service import WorkflowService
from excel_transform_1c.core.detection import detect_candidate_ranges, read_source_rows
from excel_transform_1c.core.models import IndicatorType
from excel_transform_1c.core.organization_hierarchy import (
    ExactOrganizationHierarchyResolver,
)
from tests.helpers.workbooks import (
    BDR_FULL_INDICATORS,
    bdr_full_workbook_bytes,
    erp_organization_hierarchy_bytes,
)


def _candidate_and_rows():
    workbook = load_workbook(BytesIO(bdr_full_workbook_bytes()), data_only=True)
    candidates = detect_candidate_ranges(workbook)
    assert len(candidates) == 1
    candidate = candidates[0]
    rows = read_source_rows(workbook, candidate, "БДР 2026 ИТОГ.xlsx")
    return workbook, candidate, rows


def test_bdr_detect_income_block() -> None:
    workbook, candidate, rows = _candidate_and_rows()
    try:
        assert candidate.source_kind == "bdr_full"
        assert candidate.label == "БДР 2026 ИТОГ"
        assert {
            row.article
            for row in rows
            if row.indicator_type == IndicatorType.REVENUE.value
        } == {
            "Выручка ИТОГО",
            "Прочие доходы по основной деятельности",
            "Валовая прибыль",
        }
    finally:
        workbook.close()


def test_bdr_detect_expense_block() -> None:
    workbook, _, rows = _candidate_and_rows()
    try:
        expenses = {
            row.article
            for row in rows
            if row.indicator_type == IndicatorType.EXPENSE.value
        }
        assert {
            "Административные расходы",
            "Коммерческие расходы",
            "Расходы на транспортную логистику",
            "Расходы на складскую логистику",
        }.issubset(expenses)
    finally:
        workbook.close()


def test_bdr_detect_kpi_block() -> None:
    workbook, _, rows = _candidate_and_rows()
    try:
        kpis = {
            row.article
            for row in rows
            if row.indicator_type == IndicatorType.KPI.value
        }
        assert {
            "Оборот в кг",
            "Выручка за 1 кг",
            "Итого расходов на 1 кг",
            "Валовая прибыль на 1 кг",
            "EBITDA",
            "Операционная прибыль",
        }.issubset(kpis)
    finally:
        workbook.close()


def test_bdr_full_hierarchy_resolution() -> None:
    nodes = organization_nodes(
        parse_reference_workbook(
            erp_organization_hierarchy_bytes(),
            "organizations",
        )
    )

    resolution = ExactOrganizationHierarchyResolver(nodes).resolve_exact_department(
        "000000001",
        "АЮ Административный Отдел",
    )

    assert resolution is not None
    assert resolution.organization_unit == 'ООО "Айс Юнион"'
    assert resolution.organization_unit_code == "000000001"
    assert resolution.department == "Административный департамент"
    assert resolution.cfo == "АЮ Административный Отдел"
    assert resolution.cfo_code == "000000173"


def test_bdr_export_not_empty(tmp_path) -> None:
    service = WorkflowService(tmp_path / "runtime")
    service.upload_reference("organizations", erp_organization_hierarchy_bytes())
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
    assert [candidate.label for candidate in pending.candidates] == ["БДР 2026 ИТОГ"]
    run = service.process_upload(
        pending.upload_id,
        pending.candidates[0].candidate_id,
    )

    diagnostics = service.bdr_diagnostics(run.run_id)
    assert diagnostics is not None
    assert diagnostics["rows_read"] == len(BDR_FULL_INDICATORS)
    assert diagnostics["income"] == 3
    assert diagnostics["expense"] == 5
    assert diagnostics["kpi"] == 6
    assert diagnostics["kpi_found"] == 6
    assert diagnostics["kpi_with_organization"] == 6
    assert diagnostics["kpi_with_period"] == 6
    assert diagnostics["kpi_with_value"] == 6
    assert diagnostics["kpi_exported"] == 6
    assert diagnostics["matched"] == len(BDR_FULL_INDICATORS)
    assert diagnostics["exported"] == len(BDR_FULL_INDICATORS)
    assert diagnostics["exclusions"] == []
    assert len(service.export_run(run.run_id)) > 0


def test_bdr_non_exported_indicator_has_reason(tmp_path) -> None:
    service = WorkflowService(tmp_path / "runtime")
    service.upload_reference("organizations", erp_organization_hierarchy_bytes())
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
        bdr_full_workbook_bytes(
            reporting_unit=reporting_unit,
            error_indicator="Операционная прибыль",
        ),
        context,
    )
    run = service.process_upload(
        pending.upload_id,
        pending.candidates[0].candidate_id,
    )

    diagnostics = service.bdr_diagnostics(run.run_id)
    assert diagnostics is not None
    assert diagnostics["exported"] == len(BDR_FULL_INDICATORS) - 1
    assert diagnostics["exclusions"] == [
        {
            "source_row": 41,
            "indicator": "Операционная прибыль",
            "reason": "Ошибка Excel в месячной ячейке (Произвольный сводный лист!W41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!X41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!Y41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!Z41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AA41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AB41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AC41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AD41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AE41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AF41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AG41); "
            "Ошибка Excel в месячной ячейке (Произвольный сводный лист!AH41)",
        }
    ]
