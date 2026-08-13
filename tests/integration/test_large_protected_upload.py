import asyncio
from io import BytesIO
from zipfile import is_zipfile

import pytest

from excel_transform_1c.adapters import excel as excel_adapter
from excel_transform_1c.adapters import protected_ooxml as protected_adapter
from excel_transform_1c.application.service import UPLOAD_CHUNK_SIZE, WorkflowService
from excel_transform_1c.core.models import CandidateRange
from tests.helpers.workbooks import (
    large_workbook_bytes,
    protected_workbook_bytes,
    reference_bytes,
    workbook_bytes,
)


pytestmark = pytest.mark.integration
SYNTHETIC_PASSWORD = "synthetic-test-password"


class RecordingAsyncReader:
    def __init__(self, content: bytes):
        self.source = BytesIO(content)
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.source.read(size)


def configured_service(tmp_path) -> WorkflowService:
    service = WorkflowService(tmp_path / "runtime")
    for kind in ("erp_articles", "organizations", "scenarios"):
        service.upload_reference(kind, reference_bytes(kind))
    return service


def default_context(service: WorkflowService):
    scenario = service.store.list_scenarios()[0]
    return service.build_context("ПС", "ps", scenario.scenario_id, 2026, [])


def test_async_upload_reads_only_bounded_chunks_and_preserves_exact_plain_source(tmp_path):
    service = configured_service(tmp_path)
    payload = workbook_bytes()
    source = RecordingAsyncReader(payload)

    pending = asyncio.run(
        service.prepare_upload_stream(
            "synthetic.xlsx",
            source,
            default_context(service),
            chunk_size=97,
        )
    )

    assert len(source.read_sizes) > 1
    assert set(source.read_sizes) == {97}
    assert pending.original_path.read_bytes() == payload
    assert pending.working_path == pending.original_path
    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
    assert len(run.records) == 24


def test_large_synthetic_workbook_streams_through_detection_and_preview(tmp_path):
    service = configured_service(tmp_path)
    payload = large_workbook_bytes()
    source = RecordingAsyncReader(payload)

    pending = asyncio.run(
        service.prepare_upload_stream(
            "large-synthetic.xlsx",
            source,
            default_context(service),
        )
    )
    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)

    assert 3 * UPLOAD_CHUNK_SIZE < len(payload) < 5 * UPLOAD_CHUNK_SIZE
    assert len(source.read_sizes) >= 5
    assert -1 not in source.read_sizes
    assert set(source.read_sizes) == {UPLOAD_CHUNK_SIZE}
    assert len(pending.candidates) == 1
    assert pending.candidates[0].first_data_row == 3
    assert pending.candidates[0].last_data_row == 4
    assert len(run.records) == 24


def test_protected_ooxml_uses_separate_original_and_decrypted_snapshots(tmp_path):
    service = configured_service(tmp_path)
    plain = workbook_bytes()
    protected = protected_workbook_bytes(plain, SYNTHETIC_PASSWORD)
    source = RecordingAsyncReader(protected)

    pending = asyncio.run(
        service.prepare_upload_stream(
            "protected.xlsx",
            source,
            default_context(service),
            password=SYNTHETIC_PASSWORD,
            chunk_size=257,
        )
    )

    assert pending.is_protected is True
    assert pending.original_path != pending.working_path
    assert pending.original_path.read_bytes() == protected
    assert is_zipfile(pending.working_path)

    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)
    run_path = service.run_dir / run.run_id
    assert (run_path / "source-original.xlsx").read_bytes() == protected
    assert is_zipfile(run_path / "source-working.xlsx")
    assert len(run.records) == 24


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("", "Укажите пароль"),
        ("wrong-synthetic-password", "Пароль не подошёл"),
    ],
)
def test_protected_ooxml_missing_or_wrong_password_is_business_safe(
    tmp_path,
    password,
    message,
):
    service = configured_service(tmp_path)
    protected = protected_workbook_bytes(workbook_bytes(), SYNTHETIC_PASSWORD)

    with pytest.raises(ValueError, match=message):
        asyncio.run(
            service.prepare_upload_stream(
                "protected.xlsx",
                RecordingAsyncReader(protected),
                default_context(service),
                password=password,
            )
        )

    assert service.pending == {}
    assert list(service.upload_dir.iterdir()) == []


def test_password_never_appears_in_metadata_persistence_names_or_logs(tmp_path, caplog):
    service = configured_service(tmp_path)
    protected = protected_workbook_bytes(workbook_bytes(), SYNTHETIC_PASSWORD)

    pending = asyncio.run(
        service.prepare_upload_stream(
            "protected.xlsx",
            RecordingAsyncReader(protected),
            default_context(service),
            password=SYNTHETIC_PASSWORD,
        )
    )
    run = service.process_upload(pending.upload_id, pending.candidates[0].candidate_id)

    assert SYNTHETIC_PASSWORD not in repr(pending)
    assert SYNTHETIC_PASSWORD not in repr(run)
    assert SYNTHETIC_PASSWORD not in caplog.text
    password_bytes = SYNTHETIC_PASSWORD.encode()
    for path in service.runtime_dir.rglob("*"):
        assert SYNTHETIC_PASSWORD not in path.name
        if path.is_file():
            assert password_bytes not in path.read_bytes()


def test_unknown_decrypt_exception_is_neutral_and_preserves_only_chained_cause(
    tmp_path,
    monkeypatch,
):
    synthetic_password = "synthetic-chained-cause-password"
    source = tmp_path / "source.xlsx"
    target = tmp_path / "working.xlsx"
    source.write_bytes(b"synthetic encrypted placeholder")

    def fail_with_secret(_source):
        raise RuntimeError(f"dependency exposed {synthetic_password}")

    monkeypatch.setattr(protected_adapter.msoffcrypto, "OfficeFile", fail_with_secret)

    with pytest.raises(protected_adapter.ProtectedWorkbookError) as captured:
        protected_adapter.decrypt_protected_ooxml(
            source,
            target,
            synthetic_password,
        )

    assert str(captured.value) == protected_adapter.UNKNOWN_DECRYPTION_MESSAGE
    assert synthetic_password not in str(captured.value)
    assert synthetic_password in str(captured.value.__cause__)
    assert not target.exists()


def test_unknown_decrypt_cleanup_exception_is_neutral(
    tmp_path,
    monkeypatch,
):
    synthetic_password = "synthetic-cleanup-cause-password"
    source = tmp_path / "source.xlsx"
    target = tmp_path / "working.xlsx"
    source.write_bytes(b"synthetic encrypted placeholder")

    class FailingContainer:
        def close(self):
            raise RuntimeError(f"dependency cleanup exposed {synthetic_password}")

    class OfficeFile:
        format = "ooxml"
        file = FailingContainer()

        def __init__(self, _source):
            pass

        def is_encrypted(self):
            return True

        def load_key(self, **_kwargs):
            pass

        def decrypt(self, target_file, **_kwargs):
            target_file.write(b"synthetic decrypted output")

    monkeypatch.setattr(protected_adapter.msoffcrypto, "OfficeFile", OfficeFile)

    with pytest.raises(protected_adapter.ProtectedWorkbookError) as captured:
        protected_adapter.decrypt_protected_ooxml(
            source,
            target,
            synthetic_password,
        )

    assert str(captured.value) == protected_adapter.UNKNOWN_DECRYPTION_MESSAGE
    assert synthetic_password not in str(captured.value)
    assert synthetic_password in str(captured.value.__cause__)
    assert not target.exists()


def test_budget_workbook_is_read_only_and_closed_on_success(monkeypatch):
    calls = {}

    class Workbook:
        closed = False

        def close(self):
            self.closed = True

    workbook = Workbook()

    def load_workbook(path, **kwargs):
        calls.update(kwargs)
        return workbook

    monkeypatch.setattr(excel_adapter, "load_workbook", load_workbook)
    monkeypatch.setattr(excel_adapter, "detect_candidate_ranges", lambda current: [])

    assert excel_adapter.detect_path("ignored.xlsx") == []
    assert calls == {"data_only": True, "read_only": True}
    assert workbook.closed is True


def test_budget_workbook_is_closed_when_selected_range_read_fails(monkeypatch):
    class Workbook:
        closed = False

        def close(self):
            self.closed = True

    workbook = Workbook()
    candidate = CandidateRange("candidate-1", "Sheet", 1, 2, 2, {})
    monkeypatch.setattr(excel_adapter, "load_workbook", lambda path, **kwargs: workbook)

    def fail(*args):
        raise RuntimeError("synthetic read failure")

    monkeypatch.setattr(excel_adapter, "read_source_rows", fail)

    with pytest.raises(RuntimeError, match="synthetic read failure"):
        excel_adapter.read_path("ignored.xlsx", candidate, "ignored.xlsx")
    assert workbook.closed is True
