from io import BytesIO

import pytest
from openpyxl import load_workbook

from excel_transform_1c.application.service import WorkflowService
from excel_transform_1c.core.organization_hierarchy import (
    MISSING_ERP_ELEMENT_CODE_REASON,
)
from tests.helpers.workbooks import (
    erp_organization_hierarchy_bytes,
    reference_bytes,
    workbook_bytes,
)


pytestmark = pytest.mark.integration


def _process(
    service: WorkflowService,
    organization_node_id: str,
    *,
    department: str,
    cfo: str,
):
    scenario = next(
        item for item in service.store.list_scenarios() if item.name == "ПЛАН 2026"
    )
    context = service.build_context(
        "АЮ",
        organization_node_id,
        scenario.scenario_id,
        2026,
        [],
    )
    pending = service.prepare_upload(
        "synthetic-ay-budget.xlsx",
        workbook_bytes(
            reporting_unit="АЮ",
            first_department=department,
            first_cfo=cfo,
        ),
        context,
    )
    return service.process_upload(
        pending.upload_id,
        pending.candidates[0].candidate_id,
    )


def test_export_uses_exact_erp_organization_hierarchy_codes(tmp_path) -> None:
    service = WorkflowService(tmp_path / "runtime")
    service.upload_reference(
        "organizations",
        erp_organization_hierarchy_bytes(),
    )
    service.upload_reference("intalev_cfos", reference_bytes("intalev_cfos"))
    run = _process(
        service,
        "000000001",
        department="Административный департамент",
        cfo="АЮ Административный Отдел",
    )

    first_month = next(record for record in run.records if record.source_row == 3)
    assert first_month.organization_unit == 'ООО "Айс Юнион"'
    assert first_month.organization_unit_code == "000000001"
    assert first_month.erp_department == "АЮ Административный Отдел"
    assert first_month.cfo_code == "000000173"

    service.confirm_cfo_mappings(
        run.run_id,
        [
            {
                "source_reporting_unit": "АЮ",
                "source_cfo": "АЮ Административный Отдел",
                "intalev_source_key": "code:INT-CFO-1",
                "target_node_id": "000000173",
            }
        ],
    )
    assert first_month.cfo != "АЮ Административный Отдел"

    workbook = load_workbook(BytesIO(service.export_run(run.run_id)), data_only=True)
    try:
        row = tuple(cell.value for cell in workbook["ОПИУ"][2])
        assert row[5:9] == (
            'ООО "Айс Юнион"',
            "000000001",
            "АЮ Административный Отдел",
            "000000173",
        )
    finally:
        workbook.close()


def test_exact_name_without_code_marks_record_attention(tmp_path) -> None:
    service = WorkflowService(tmp_path / "runtime")
    service.upload_reference(
        "organizations",
        erp_organization_hierarchy_bytes(cfo_code=""),
    )
    run = _process(
        service,
        "000000001",
        department="Административный департамент",
        cfo="АЮ Административный Отдел",
    )

    first_month = next(record for record in run.records if record.source_row == 3)
    assert first_month.cfo_code == ""
    assert first_month.status == "Требует внимания"
    assert MISSING_ERP_ELEMENT_CODE_REASON in first_month.reasons
