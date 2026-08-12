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
    STATUS_SKIPPED,
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

        original = row_records[0]
        for field, selected in changes.items():
            original_value = original.erp_code if field == "erp_code" else str(getattr(original, field))
            self.store.save_override(run_id, source_row, field, original_value, selected)

        path_changed = bool({"expense_group", "source_article"}.intersection(changes))
        mapping_reason: str | None = None
        mapped_article: ERPArticle | None = None
        for record in row_records:
            for field, selected in changes.items():
                if field != "erp_code":
                    setattr(record, field, selected)

        if "erp_code" in changes:
            mapped_article = by_code[changes["erp_code"]]
        elif path_changed:
            representative = row_records[0]
            mapper = ExactERPMapper(articles, self.store.load_manual_mappings())
            mapped_article, mapping_reason = mapper.resolve(
                representative.expense_type,
                representative.expense_group,
                representative.source_article,
            )

        if "erp_code" in changes or path_changed:
            for record in row_records:
                record.erp_code = mapped_article.code if mapped_article else ""
                record.erp_article_name = mapped_article.name if mapped_article else ""

        if "erp_code" in changes:
            self.store.save_manual_mapping(row_records[0].mapping_key, changes["erp_code"])

        for record in row_records:
            self._refresh_record(record, by_code, mapping_reason)

        self._resolve_row_issues(run, source_row, changes)
        if path_changed and "erp_code" not in changes and mapping_reason:
            pointer_key = "article" if "source_article" in changes else "expense_group"
            record = row_records[0]
            run.issues.append(
                Issue(
                    issue_id=uuid4().hex,
                    kind="erp-mapping",
                    description=mapping_reason,
                    pointer=record.pointers[pointer_key],
                    reporting_unit=record.reporting_unit,
                    department=record.department,
                    cfo=record.cfo,
                    expense_type=record.expense_type,
                    expense_group=record.expense_group,
                    article=record.source_article,
                    raw_value=record.source_article,
                )
            )
        return run

    def _refresh_record(
        self,
        record,
        by_code: dict[str, ERPArticle],
        mapping_reason: str | None = None,
    ) -> None:
        removable = (
            "Точное соответствие ERP",
            "Точный путь соответствует",
            "Сохранённое соответствие",
            "Сохранённое ручное соответствие",
            "Налогообложение",
            "Числовой 0",
            "Выбранный ERP-код",
            "Не заполнено поле: department",
            "Не заполнено поле: cfo",
            "Не заполнено поле: expense_group",
            "Не заполнено поле: article",
        )
        record.reasons = [reason for reason in record.reasons if not reason.startswith(removable)]
        for field in ("department", "cfo", "expense_group", "source_article"):
            if not getattr(record, field):
                source_field = "article" if field == "source_article" else field
                record.reasons.append(f"Не заполнено поле: {source_field}")
        if mapping_reason:
            record.reasons.append(mapping_reason)
        elif not record.erp_code:
            record.reasons.append("Точное соответствие ERP не найдено")
        elif record.erp_code not in by_code:
            record.reasons.append("Выбранный ERP-код отсутствует в текущем справочнике")
        tax_reason = normalize_tax(record.tax)[1]
        if tax_reason:
            record.reasons.append(tax_reason)
        if record.status != STATUS_SKIPPED:
            record.status = STATUS_ATTENTION if record.reasons else STATUS_OK

    def _resolve_row_issues(self, run: ProcessedRun, source_row: int, changes: dict[str, str]) -> None:
        pointers_by_field = {
            "department": "department",
            "cfo": "cfo",
            "expense_group": "expense_group",
            "source_article": "article",
        }
        for issue in run.issues:
            if issue.pointer.row != source_row:
                continue
            if "erp_code" in changes and issue.kind == "erp-mapping":
                issue.resolved = True
            elif {"expense_group", "source_article"}.intersection(changes) and issue.kind == "erp-mapping":
                issue.resolved = True
            elif "tax" in changes and issue.kind == "tax":
                issue.resolved = True
            elif issue.kind == "shared-field" and any(
                issue.pointer.field == pointer
                for field, pointer in pointers_by_field.items()
                if field in changes
            ):
                issue.resolved = True

    def export_run(self, run_id: str) -> bytes:
        return export_opiu_light(self.get_run(run_id).visible_records())
