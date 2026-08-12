from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from excel_transform_1c.adapters.excel import detect_path, export_opiu_light, read_path
from excel_transform_1c.adapters.persistence import LocalStore
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
    ProcessedRun,
    RunContext,
    STATUS_ATTENTION,
    STATUS_OK,
)
from excel_transform_1c.core.transform import ExactERPMapper, normalize_tax, transform_rows


@dataclass
class PendingUpload:
    upload_id: str
    source_name: str
    path: Path
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

    def prepare_upload(self, source_name: str, content: bytes, context: RunContext) -> PendingUpload:
        if not source_name.lower().endswith((".xlsx", ".xlsm")):
            raise ValueError("Поддерживаются файлы .xlsx и .xlsm")
        upload_id = uuid4().hex
        path = self.upload_dir / f"{upload_id}.xlsx"
        path.write_bytes(content)
        try:
            candidates = detect_path(path)
        except Exception as exc:
            path.unlink(missing_ok=True)
            raise ValueError("Файл не открывается или повреждён") from exc
        pending = PendingUpload(upload_id, Path(source_name).name, path, candidates, context)
        self.pending[upload_id] = pending
        return pending

    def reset_upload(self, upload_id: str) -> None:
        pending = self.pending.pop(upload_id, None)
        if pending:
            pending.path.unlink(missing_ok=True)

    def process_upload(self, upload_id: str, candidate_id: str) -> ProcessedRun:
        pending = self.pending.get(upload_id)
        if not pending:
            raise ValueError("Загрузка не найдена; выберите файл повторно")
        candidate = next((item for item in pending.candidates if item.candidate_id == candidate_id), None)
        if not candidate:
            raise ValueError("Выберите распознанный диапазон")
        digest = hashlib.sha256(pending.path.read_bytes()).hexdigest()
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
        snapshot = snapshot_dir / "source.xlsx"
        shutil.copyfile(pending.path, snapshot)
        rows = read_path(snapshot, candidate, pending.source_name)
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
        allowed_fields = {"erp_code", "tax", "department", "cfo", "expense_group", "source_article"}
        changes = {field: value for field, value in changes.items() if field in allowed_fields and value != ""}
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

        for record in row_records:
            original_key = record.mapping_key
            for field, selected in changes.items():
                if field == "erp_code":
                    original = record.erp_code
                    article = by_code[selected]
                    record.erp_code = article.code
                    record.erp_article_name = article.name
                else:
                    original = str(getattr(record, field))
                    setattr(record, field, selected)
                self.store.save_override(run_id, source_row, field, original, selected)
            if "erp_code" in changes:
                self.store.save_manual_mapping(original_key, changes["erp_code"])
            self._refresh_record(record, by_code)

        self._resolve_row_issues(run, source_row, changes)
        return run

    def _refresh_record(self, record, by_code: dict[str, ERPArticle]) -> None:
        removable = (
            "Точное соответствие ERP",
            "Точный путь соответствует",
            "Сохранённое соответствие",
            "Налогообложение",
            "Числовой 0",
            "Не заполнено поле: department",
            "Не заполнено поле: cfo",
            "Не заполнено поле: expense_group",
            "Не заполнено поле: article",
        )
        record.reasons = [reason for reason in record.reasons if not reason.startswith(removable)]
        if not record.erp_code:
            record.reasons.append("Точное соответствие ERP не найдено")
        elif record.erp_code not in by_code:
            record.reasons.append("Выбранный ERP-код отсутствует в текущем справочнике")
        if normalize_tax(record.tax)[1]:
            record.reasons.append(normalize_tax(record.tax)[1] or "")
        record.status = STATUS_ATTENTION if record.reasons else STATUS_OK

    def _resolve_row_issues(self, run: ProcessedRun, source_row: int, changes: dict[str, str]) -> None:
        kinds_by_field = {
            "erp_code": {"erp-mapping"},
            "tax": {"tax"},
            "department": {"shared-field"},
            "cfo": {"shared-field"},
            "expense_group": {"shared-field", "erp-mapping"},
            "source_article": {"shared-field", "erp-mapping"},
        }
        resolved_kinds = set().union(*(kinds_by_field[field] for field in changes)) if changes else set()
        for issue in run.issues:
            if issue.pointer.row == source_row and issue.kind in resolved_kinds:
                issue.resolved = True

    def export_run(self, run_id: str) -> bytes:
        return export_opiu_light(self.get_run(run_id).visible_records())
