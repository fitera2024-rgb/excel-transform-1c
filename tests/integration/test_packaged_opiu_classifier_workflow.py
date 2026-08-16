from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook

from excel_transform_1c.application.service import WorkflowService
from excel_transform_1c.core.indicator_matching import INDICATOR_INCOMPLETE
from tests.helpers.workbooks import HEADERS


pytestmark = pytest.mark.integration


def _expense_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Расходы"
    sheet.append(HEADERS)
    sheet.append(
        [
            "ПС",
            "Административные расходы",
            "Департамент",
            "ТК",
            "ЦФО",
            "БЕЗ НДС",
            "Командировочные",
            "Проживание",
            100,
            *([0] * 11),
        ]
    )
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_clean_install_applies_packaged_mxl_link_without_inventing_channel(tmp_path):
    service = WorkflowService(tmp_path / "runtime")
    organization = service.organization_nodes()[0]
    scenario = service.store.list_scenarios()[0]
    context = service.build_context(
        "ПС",
        organization.node_id,
        scenario.scenario_id,
        2026,
        [],
    )
    pending = service.prepare_upload("expense.xlsx", _expense_workbook(), context)
    run = service.process_upload(
        pending.upload_id,
        pending.candidates[0].candidate_id,
    )

    assert run.indicator_classifier_loaded is True
    assert service.indicator_counts(run.run_id) == {
        "automatic": 0,
        "attention": 1,
        "not_found": 0,
    }
    record = run.records[0]
    assert record.indicator == "Административные расходы"
    assert record.indicator_match_status == INDICATOR_INCOMPLETE
    assert record.indicator_match_reason == "В точной связи не заполнен канал сбыта"

    exported = load_workbook(BytesIO(service.export_run(run.run_id)), data_only=True)
    try:
        assert exported.sheetnames == ["OPIU Light", "ОПИУ", "Показатели"]
        assert exported["Показатели"].max_row == 1
    finally:
        exported.close()
