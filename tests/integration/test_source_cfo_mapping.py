from __future__ import annotations

from excel_transform_1c.application.service import WorkflowService
from tests.helpers.workbooks import reference_bytes, workbook_bytes


def _service(tmp_path) -> WorkflowService:
    service = WorkflowService(tmp_path / "runtime")
    for kind in ("erp_articles", "organizations", "scenarios", "intalev_cfos"):
        service.upload_reference(kind, reference_bytes(kind))
    return service


def _context(service: WorkflowService):
    scenario = service.store.list_scenarios()[0]
    return service.build_context("ПС", "ps", scenario.scenario_id, 2026, [])


def _process(service: WorkflowService, payload: bytes):
    pending = service.prepare_upload("synthetic-cfo.xlsx", payload, _context(service))
    return service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)


def test_explicit_source_cfo_to_intalev_to_1c_mapping_updates_all_months_and_persists(
    tmp_path,
):
    service = _service(tmp_path)
    run = _process(
        service,
        workbook_bytes(cfo_error=False, second_cfo="Исходный отдел"),
    )

    entries = service.cfo_mapping_entries(run.run_id)
    raw_entry = next(item for item in entries if item["source_cfo"] == "Исходный отдел")
    assert raw_entry["intalev_source_key"] == ""
    assert raw_entry["confirmed"] is False
    assert raw_entry["eligible"] is True
    assert "не сопоставлен" in raw_entry["status"]

    updated, count = service.confirm_cfo_mappings(
        run.run_id,
        [
            {
                "source_reporting_unit": "ПС",
                "source_cfo": "Исходный отдел",
                "intalev_source_key": "code:INT-CFO-2",
                "target_node_id": "other",
            }
        ],
    )
    assert count == 1

    source_records = [
        record for record in updated.records if record.source_cfo == "Исходный отдел"
    ]
    assert len(source_records) == 12
    assert {record.source_cfo_key for record in source_records} == {"code:INT-CFO-2"}
    assert {record.cfo_target_node_id for record in source_records} == {"other"}
    assert {record.cfo_mapping_confirmed for record in source_records} == {True}
    assert all(
        "Исходный ЦФО не сопоставлен с ЦФО Инталев" not in record.reasons
        for record in source_records
    )

    restarted = WorkflowService(service.runtime_dir)
    assert restarted.store.load_source_cfo_mappings()[("ПС", "Исходный отдел")] == (
        "code:INT-CFO-2"
    )
    assert restarted.store.load_cfo_mappings()["code:INT-CFO-2"] == "other"


def test_source_cfo_resolution_is_exact_and_does_not_guess_by_case(tmp_path):
    service = _service(tmp_path)
    run = _process(
        service,
        workbook_bytes(cfo_error=False, second_cfo="цфо 2"),
    )

    entry = next(item for item in service.cfo_mapping_entries(run.run_id) if item["source_cfo"] == "цфо 2")
    assert entry["intalev_source_key"] == ""
    assert entry["intalev_confirmed"] is False
    assert "не сопоставлен" in entry["status"]
