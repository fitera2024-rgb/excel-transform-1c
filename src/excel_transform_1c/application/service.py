from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from excel_transform_1c.adapters.excel import detect_path, export_opiu_light, read_path
from excel_transform_1c.adapters.persistence import LocalStore
from excel_transform_1c.adapters.protected_ooxml import (
    ProtectedWorkbookError,
    decrypt_protected_ooxml,
    has_ole_signature,
)
from excel_transform_1c.adapters.references import (
    erp_articles,
    organization_nodes,
    parse_reference_workbook,
)
from excel_transform_1c.core.access import effective_organization_nodes
from excel_transform_1c.core.models import (
    CandidateRange,
    ERPArticle,
    Issue,
    OrganizationNode,
    PreviewRecord,
    ProcessedRun,
    RunContext,
    STATUS_ATTENTION,
    STATUS_OK,
    STATUS_SKIPPED,
)
from excel_transform_1c.core.transform import ExactERPMapper, normalize_tax, transform_rows


UPLOAD_CHUNK_SIZE = 1024 * 1024


@dataclass
class PendingUpload:
    upload_id: str
    source_name: str
    original_path: Path
    working_path: Path
    is_protected: bool
    candidates: list[CandidateRange]
    context: RunContext


class WorkflowService:
    def __init__(self, runtime_dir: str | Path):
        self.runtime_dir = Path(runtime_dir)
        self.upload_dir = self.runtime_dir / "uploads"
        self.run_dir = self.runtime_dir / "runs"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.store = LocalStore(self.runtime_dir / "local.db")
        self.pending: dict[str, PendingUpload] = {}
        self.runs: dict[str, ProcessedRun] = {}
        self.run_keys: dict[str, str] = {}

    def reference_counts(self) -> dict[str, int]:
        return {
            "erp_articles": len(self.store.load_reference("erp_articles")),
            "organizations": len(self.store.load_reference("organizations")),
            "scenarios": len(self.store.list_scenarios()),
        }

    def upload_reference(self, kind: str, content: bytes) -> int:
        payload = parse_reference_workbook(content, kind)
        if kind == "scenarios":
            for item in payload:
                self.store.add_scenario(
                    name=item["name"],
                    year=int(item["year"]),
                    comment=item.get("comment", ""),
                    erp_code=item.get("erp_code") or None,
                    erp_confirmed=bool(item.get("erp_code")),
                )
        else:
            self.store.replace_reference(kind, payload)
        return len(payload)

    def erp_articles(self) -> list[ERPArticle]:
        return erp_articles(self.store.load_reference("erp_articles"))

    def organization_nodes(self) -> list[OrganizationNode]:
        return organization_nodes(self.store.load_reference("organizations"))

    def allowed_organization_nodes(self, user_key: str = "local") -> list[OrganizationNode]:
        nodes = self.organization_nodes()
        delegated = self.store.get_delegations(user_key)
        return effective_organization_nodes(nodes, delegated) if delegated else nodes

    def set_delegations(self, node_ids: list[str], user_key: str = "local") -> None:
        self.store.set_delegations(user_key, node_ids)

    def build_context(
        self,
        reporting_unit: str,
        organization_node_id: str,
        scenario_id: str,
        year: int | None,
        months: list[int],
    ) -> RunContext:
        allowed = {node.node_id: node for node in self.allowed_organization_nodes()}
        if organization_node_id not in allowed:
            raise ValueError("Выберите разрешённый организационный узел")
        scenarios = {scenario.scenario_id: scenario for scenario in self.store.list_scenarios()}
        if scenario_id not in scenarios:
            raise ValueError("Выберите сценарий")
        scenario = scenarios[scenario_id]
        selected_year = year or scenario.year
        if not selected_year:
            raise ValueError("Укажите год")
        if any(month < 1 or month > 12 for month in months):
            raise ValueError("Месяц должен быть от 1 до 12")
        node = allowed[organization_node_id]
        return RunContext(
            reporting_unit=reporting_unit,
            organization_node_id=node.node_id,
            organization_name=f"{node.full_path} ({node.code})",
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            scenario_year=scenario.year,
            scenario_erp_confirmed=scenario.erp_confirmed,
            year=selected_year,
            selected_months=tuple(sorted(set(months))),
        )

    def prepare_upload(
        self,
        source_name: str,
        content: bytes | BinaryIO,
        context: RunContext,
        password: str = "",
        chunk_size: int = UPLOAD_CHUNK_SIZE,
    ) -> PendingUpload:
        """Stage a small/test input through the same bounded-copy path as HTTP uploads."""

        if chunk_size <= 0:
            raise ValueError("Размер блока загрузки должен быть положительным")
        source = BytesIO(content) if isinstance(content, bytes) else content
        upload_id, original_path = self._new_upload_target(source_name)
        try:
            with original_path.open("xb") as target:
                while chunk := source.read(chunk_size):
                    target.write(chunk)
            return self._prepare_staged_upload(
                upload_id,
                source_name,
                original_path,
                context,
                password,
            )
        except Exception:
            shutil.rmtree(original_path.parent, ignore_errors=True)
            raise

    async def prepare_upload_stream(
        self,
        source_name: str,
        source: Any,
        context: RunContext,
        password: str = "",
        chunk_size: int = UPLOAD_CHUNK_SIZE,
    ) -> PendingUpload:
        """Stream an UploadFile-like source, then analyze it outside the event loop."""

        if chunk_size <= 0:
            raise ValueError("Размер блока загрузки должен быть положительным")
        upload_id, original_path = self._new_upload_target(source_name)
        try:
            with original_path.open("xb") as target:
                while chunk := await source.read(chunk_size):
                    target.write(chunk)
            return await asyncio.to_thread(
                self._prepare_staged_upload,
                upload_id,
                source_name,
                original_path,
                context,
                password,
            )
        except Exception:
            shutil.rmtree(original_path.parent, ignore_errors=True)
            raise

    def _new_upload_target(self, source_name: str) -> tuple[str, Path]:
        if not source_name.lower().endswith((".xlsx", ".xlsm")):
            raise ValueError("Поддерживаются файлы .xlsx и .xlsm")
        upload_id = uuid4().hex
        upload_path = self.upload_dir / upload_id
        upload_path.mkdir(parents=True, exist_ok=False)
        suffix = Path(source_name).suffix.lower()
        return upload_id, upload_path / f"source-original{suffix}"

    def _prepare_staged_upload(
        self,
        upload_id: str,
        source_name: str,
        original_path: Path,
        context: RunContext,
        password: str,
    ) -> PendingUpload:
        is_protected = has_ole_signature(original_path)
        working_path = original_path
        try:
            if is_protected:
                working_path = original_path.parent / "source-working.xlsx"
                decrypt_protected_ooxml(original_path, working_path, password)
            candidates = detect_path(working_path)
        except ProtectedWorkbookError:
            raise
        except Exception as exc:
            raise ValueError("Файл не открывается или повреждён") from exc
        pending = PendingUpload(
            upload_id=upload_id,
            source_name=Path(source_name).name,
            original_path=original_path,
            working_path=working_path,
            is_protected=is_protected,
            candidates=candidates,
            context=context,
        )
        self.pending[upload_id] = pending
        return pending

    def reset_upload(self, upload_id: str) -> None:
        pending = self.pending.pop(upload_id, None)
        if pending:
            shutil.rmtree(pending.original_path.parent, ignore_errors=True)

    def process_upload(self, upload_id: str, candidate_id: str) -> ProcessedRun:
        pending = self.pending.get(upload_id)
        if not pending:
            raise ValueError("Загрузка не найдена; выберите файл повторно")
        candidate = next(
            (item for item in pending.candidates if item.candidate_id == candidate_id),
            None,
        )
        if not candidate:
            raise ValueError("Выберите распознанный диапазон")
        digest = self._sha256_path(pending.original_path)
        run_key = json.dumps(
            [digest, candidate.candidate_id, pending.context.__dict__],
            ensure_ascii=False,
            sort_keys=True,
            default=list,
        )
        if run_key in self.run_keys:
            return self.runs[self.run_keys[run_key]]

        run_id = uuid4().hex
        snapshot_dir = self.run_dir / run_id
        snapshot_dir.mkdir(parents=True, exist_ok=False)
        original_snapshot = snapshot_dir / pending.original_path.name
        shutil.copyfile(pending.original_path, original_snapshot)
        processing_snapshot = original_snapshot
        if pending.is_protected:
            processing_snapshot = snapshot_dir / "source-working.xlsx"
            shutil.copyfile(pending.working_path, processing_snapshot)
        rows = read_path(processing_snapshot, candidate, pending.source_name)
        mapper = ExactERPMapper(self.erp_articles(), self.store.load_manual_mappings())
        records, issues = transform_rows(rows, pending.context, mapper)
        run = ProcessedRun(
            run_id=run_id,
            context=pending.context,
            source_file=pending.source_name,
            candidate=candidate,
            records=records,
            issues=issues,
            created_at=datetime.now(UTC).isoformat(),
        )
        self.runs[run_id] = run
        self.run_keys[run_key] = run_id
        return run

    @staticmethod
    def _sha256_path(path: Path, chunk_size: int = UPLOAD_CHUNK_SIZE) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()

    def get_run(self, run_id: str) -> ProcessedRun:
        if run_id not in self.runs:
            raise KeyError(run_id)
        return self.runs[run_id]

    def correct_row(self, run_id: str, source_row: int, changes: dict[str, str]) -> ProcessedRun:
        run = self.get_run(run_id)
        row_records = [record for record in run.records if record.source_row == source_row]
        if not row_records:
            raise ValueError("Исходная строка не найдена")

        articles = self.erp_articles()
        by_code = {article.code: article for article in articles}
        allowed_fields = {
            "erp_code",
            "tax",
            "department",
            "cfo",
            "expense_group",
            "source_article",
        }
        changes = {
            field: value
            for field, value in changes.items()
            if field in allowed_fields and value != ""
        }
        if not changes:
            return run

        if "erp_code" in changes and changes["erp_code"] not in by_code:
            raise ValueError("Выберите ERP-код из загруженного справочника")

        org_values = {node.full_path for node in self.organization_nodes()}
        for field in ("department", "cfo"):
            if field in changes and changes[field] not in org_values:
                raise ValueError("Выберите организационное значение из загруженного дерева")

        valid_groups = {article.expense_group for article in articles}
        valid_articles = {article.source_article for article in articles}
        if "expense_group" in changes and changes["expense_group"] not in valid_groups:
            raise ValueError("Выберите группу из загруженного справочника")
        if "source_article" in changes and changes["source_article"] not in valid_articles:
            raise ValueError("Выберите статью из загруженного справочника")
        if "tax" in changes and normalize_tax(changes["tax"])[1]:
            raise ValueError("Выберите допустимое налогообложение")

        first = row_records[0]
        for field, selected in changes.items():
            original = str(getattr(first, field))
            self.store.save_override(run_id, source_row, field, original, selected)

        for record in row_records:
            for field, selected in changes.items():
                if field == "erp_code":
                    article = by_code[selected]
                    record.erp_code = article.code
                    record.erp_article_name = article.name
                else:
                    setattr(record, field, selected)

        if "erp_code" in changes:
            self.store.save_manual_mapping(row_records[0].mapping_key, changes["erp_code"])
        elif {"expense_group", "source_article"}.intersection(changes):
            for record in row_records:
                record.erp_code = ""
                record.erp_article_name = ""

        self._rebuild_row_state(run, source_row)
        return run

    def _rebuild_row_state(self, run: ProcessedRun, source_row: int) -> None:
        row_records = [record for record in run.records if record.source_row == source_row]
        if not row_records:
            return
        base = row_records[0]

        recomputed_shared_fields = {
            "expense_type",
            "department",
            "organization_type",
            "cfo",
            "expense_group",
            "source_article",
        }
        for issue in run.issues:
            if issue.pointer.row != source_row or issue.resolved:
                continue
            if issue.kind in {"tax", "erp-mapping"}:
                issue.resolved = True
            elif issue.kind == "shared-field" and issue.pointer.field in recomputed_shared_fields:
                issue.resolved = True

        persistent_common = [
            issue.description
            for issue in run.issues
            if not issue.resolved
            and issue.pointer.row == source_row
            and issue.kind in {"context-reporting-unit"}
        ]
        persistent_reporting_missing = [
            issue.description
            for issue in run.issues
            if not issue.resolved
            and issue.pointer.row == source_row
            and issue.kind == "shared-field"
            and issue.pointer.field == "reporting_unit"
        ]

        dynamic_reasons: list[str] = []
        field_values = {
            "expense_type": base.expense_type,
            "department": base.department,
            "organization_type": base.organization_type,
            "cfo": base.cfo,
            "expense_group": base.expense_group,
            "source_article": base.source_article,
        }
        field_labels = {
            "expense_type": "тип расходов",
            "department": "департамент",
            "organization_type": "вид организации",
            "cfo": "отдел / ЦФО",
            "expense_group": "группа расходов",
            "source_article": "статья",
        }
        for field, value in field_values.items():
            if value == "":
                reason = f"Не заполнено поле: {field_labels[field]}"
                dynamic_reasons.append(reason)
                run.issues.append(self._issue_from_record(base, "shared-field", reason, field, value))

        tax_reason = normalize_tax(base.tax)[1]
        if tax_reason:
            dynamic_reasons.append(tax_reason)
            run.issues.append(self._issue_from_record(base, "tax", tax_reason, "tax", base.tax))

        mapper = ExactERPMapper(self.erp_articles(), self.store.load_manual_mappings())
        mapped, mapping_reason = mapper.resolve(
            base.expense_type,
            base.expense_group,
            base.source_article,
        )
        for record in row_records:
            record.erp_code = mapped.code if mapped else ""
            record.erp_article_name = mapped.name if mapped else ""
        if mapping_reason:
            dynamic_reasons.append(mapping_reason)
            run.issues.append(
                self._issue_from_record(
                    base,
                    "erp-mapping",
                    mapping_reason,
                    "source_article",
                    base.source_article,
                )
            )

        common_reasons = [
            *persistent_common,
            *persistent_reporting_missing,
            *dynamic_reasons,
        ]
        if not run.context.scenario_erp_confirmed:
            common_reasons.append("Сценарий не подтверждён справочником ERP")

        monthly_issues = {
            issue.pointer.month: issue.description
            for issue in run.issues
            if not issue.resolved
            and issue.pointer.row == source_row
            and issue.kind == "monthly-error"
        }

        for record in row_records:
            reasons = list(common_reasons)
            if record.amount is None:
                skip_reason = monthly_issues.get(record.month, "Месячная запись не сформирована")
                pointer = record.pointers["amount"]
                reasons.append(f"{skip_reason} ({pointer.sheet}!{pointer.cell})")
                record.status = STATUS_SKIPPED
            else:
                if record.amount < 0:
                    reasons.append("Отрицательная сумма")
                record.status = STATUS_ATTENTION if reasons else STATUS_OK
            record.reasons = reasons

    @staticmethod
    def _issue_from_record(
        record: PreviewRecord,
        kind: str,
        description: str,
        field: str,
        raw_value: Any,
    ) -> Issue:
        return Issue(
            issue_id=uuid4().hex,
            kind=kind,
            description=description,
            pointer=record.pointers[field],
            reporting_unit=record.reporting_unit,
            department=record.department,
            cfo=record.cfo,
            expense_type=record.expense_type,
            expense_group=record.expense_group,
            article=record.source_article,
            raw_value="" if raw_value is None else str(raw_value),
        )

    def export_run(self, run_id: str) -> bytes:
        return export_opiu_light(self.get_run(run_id).visible_records())
