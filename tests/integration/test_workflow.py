from io import BytesIO

import pytest
from openpyxl import load_workbook

from excel_transform_1c.adapters.excel import EXPORT_HEADERS, detect_path, export_opiu_light, read_path
from excel_transform_1c.adapters.persistence import LocalStore
from excel_transform_1c.application.service import WorkflowService
from tests.helpers.workbooks import reference_bytes, workbook_bytes, write_cached_formula_fixture


pytestmark = pytest.mark.integration


def configured_service(tmp_path) -> WorkflowService:
    service = WorkflowService(tmp_path / "runtime")
    for kind in ("erp_articles", "organizations", "scenarios"):
        service.upload_reference(kind, reference_bytes(kind))
    return service


def default_context(service: WorkflowService, months=None):
    scenario = service.store.list_scenarios()[0]
    return service.build_context("ПС", "ps", scenario.scenario_id, 2026, months or [])


def test_arbitrary_sheet_name_and_24_record_workflow(tmp_path):
    service = configured_service(tmp_path)
    pending = service.prepare_upload("synthetic.xlsx", workbook_bytes(sheet_name="Совсем другое имя"), default_context(service))
    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
    assert run.candidate.sheet == "Совсем другое имя"
    assert len(run.records) == 24


def test_two_candidates_require_explicit_selection_and_single_flight(tmp_path):
    service = configured_service(tmp_path)
    pending = service.prepare_upload("synthetic.xlsx", workbook_bytes(two_candidates=True), default_context(service))
    assert len(pending.candidates) == 2
    first = service.process_upload(pending.upload_id, pending.candidates[1].candidate_id)
    second = service.process_upload(pending.upload_id, pending.candidates[1].candidate_id)
    assert first.run_id == second.run_id
    assert len(service.runs) == 1


def test_broken_and_no_range_workbooks_are_blocked(tmp_path):
    service = configured_service(tmp_path)
    with pytest.raises(ValueError, match="повреждён"):
        service.prepare_upload("bad.xlsx", b"not an xlsx", default_context(service))
    pending = service.prepare_upload("empty.xlsx", workbook_bytes(no_range=True), default_context(service))
    assert pending.candidates == []


def test_cached_formula_value_is_read_without_excel_recalculation(tmp_path):
    path = tmp_path / "cached.xlsx"
    write_cached_formula_fixture(path)
    candidate = detect_path(path)[0]
    rows = read_path(path, candidate, "cached.xlsx")
    assert rows[0].months[0] == 100


def test_local_persistence_survives_restart_and_keeps_mapping(tmp_path):
    database = tmp_path / "local.db"
    first = LocalStore(database)
    scenario = first.add_scenario("ПЛАН 2027", 2027, "synthetic")
    key = ("ОтчетОПрибыляхИУбытках", "Тип", "Группа", "Статья")
    first.save_manual_mapping(key, "ERP-001")
    second = LocalStore(database)
    assert second.list_scenarios()[0].scenario_id == scenario.scenario_id
    assert second.load_manual_mappings()[key] == "ERP-001"


def test_month_filter_does_not_destroy_full_result_and_export_schema_is_business_only(tmp_path):
    service = configured_service(tmp_path)
    pending = service.prepare_upload("synthetic.xlsx", workbook_bytes(), default_context(service, [1, 2]))
    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
    assert len(run.records) == 24
    assert len(run.visible_records()) == 4
    payload = service.export_run(run.run_id)
    workbook = load_workbook(BytesIO(payload), data_only=True)
    sheet = workbook["OPIU Light"]
    assert tuple(cell.value for cell in sheet[1]) == EXPORT_HEADERS
    assert sheet.max_row == 5
    forbidden = {"SHA", "BatchID", "Proof JSON", "Internal path", "RUN-ID"}
    assert not forbidden.intersection(EXPORT_HEADERS)


def test_user_correction_updates_preview_and_registry_without_rerun(tmp_path):
    service = configured_service(tmp_path)
    pending = service.prepare_upload("synthetic.xlsx", workbook_bytes(missing_mapping=True), default_context(service))
    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
    before_count = len(run.unresolved_issues)
    before_id = run.run_id
    service.correct_row(run.run_id, 3, {"erp_code": "ERP-001"})
    assert run.run_id == before_id
    assert run.rerun_count == 0
    assert all(record.erp_code == "ERP-001" for record in run.records if record.source_row == 3)
    assert len(run.unresolved_issues) < before_count
    assert service.store.load_manual_mappings()


def test_manual_mapping_reuses_only_same_accepted_key(tmp_path):
    service = configured_service(tmp_path)
    pending = service.prepare_upload("first.xlsx", workbook_bytes(missing_mapping=True), default_context(service))
    first = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
    service.correct_row(first.run_id, 3, {"erp_code": "ERP-001"})
    pending_two = service.prepare_upload(
        "second.xlsx",
        workbook_bytes(sheet_name="Другой synthetic лист", missing_mapping=True),
        default_context(service),
    )
    second = service.process_upload(pending_two.upload_id, pending_two.candidates[0].candidate_id)
    # The confirmed choice is reused by report type + exact source path only.
    assert all(record.erp_code == "ERP-001" for record in second.records if record.source_row == 3)
    assert not any(issue.kind == "erp-mapping" and issue.pointer.row == 3 for issue in second.issues)
