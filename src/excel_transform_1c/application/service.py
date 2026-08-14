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
    intalev_cfos,
    organization_nodes,
    parse_reference_workbook,
)
from excel_transform_1c.core.access import effective_organization_nodes
from excel_transform_1c.core.models import (
    CandidateRange,
    ERPArticle,
    IntalevCFO,
    Issue,
    OrganizationNode,
    PreviewRecord,
    ProcessedRun,
    RunContext,
    STATUS_ATTENTION,
    STATUS_OK,
    STATUS_SKIPPED,
    TAX_NOT_REQUIRED,
)
from excel_transform_1c.core.transform import ExactERPMapper, normalize_tax, transform_rows


UPLOAD_CHUNK_SIZE = 1024 * 1024
INLINE_EDITABLE_ISSUE_KINDS = frozenset({"erp-mapping", "tax", "cfo-mapping"})
INLINE_EDITABLE_SHARED_FIELDS = frozenset(
    {"department", "cfo", "expense_group", "source_article"}
)


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
            "intalev_cfos": len(self.store.load_reference("intalev_cfos")),
        }

    def upload_reference(self, kind: str, content: bytes) -> int:
        payload = parse_reference_workbook(content, kind)
        if kind == "scenarios":
            self.store.merge_scenarios(payload)
        else:
            self.store.replace_reference(kind, payload)
        return len(payload)

    def erp_articles(self) -> list[ERPArticle]:
        return erp_articles(self.store.load_reference("erp_articles"))

    def organization_nodes(self) -> list[OrganizationNode]:
        return organization_nodes(self.store.load_reference("organizations"))

    def intalev_cfos(self) -> list[IntalevCFO]:
        return intalev_cfos(self.store.load_reference("intalev_cfos"))

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
        if not source_name.lower().endswith((".xlsx", ".xlsm", ".xls")):
            raise ValueError("Поддерживаются файлы .xlsx, .xlsm и .xls")
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
            cfo_mapping_enabled=bool(self.intalev_cfos()),
        )
        if run.cfo_mapping_enabled:
            self._initialize_cfo_mappings(run)
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

    @staticmethod
    def _issue_is_inline_editable(issue: Issue) -> bool:
        return issue.kind in INLINE_EDITABLE_ISSUE_KINDS or (
            issue.kind == "shared-field"
            and issue.pointer.field in INLINE_EDITABLE_SHARED_FIELDS
        )

    def bulk_confirmable_source_rows(self, run_id: str) -> list[int]:
        """Return attention source rows whose current ERP mapping is fully valid."""

        run = self.get_run(run_id)
        editable_rows = {
            issue.pointer.row
            for issue in run.unresolved_issues
            if self._issue_is_inline_editable(issue)
        }
        catalog = {
            (article.expense_type, article.expense_group, article.source_article, article.code)
            for article in self.erp_articles()
        }
        eligible: set[int] = set()
        for record in run.records:
            if record.source_row not in editable_rows or record.source_row in eligible:
                continue
            signature = (
                record.expense_type,
                record.expense_group,
                record.source_article,
                record.erp_code,
            )
            if record.erp_code and signature in catalog:
                eligible.add(record.source_row)
        return sorted(eligible)

    def confirmed_erp_source_rows(self, run_id: str) -> set[int]:
        run = self.get_run(run_id)
        manual_mappings = self.store.load_manual_mappings()
        return {
            record.source_row
            for record in run.records
            if record.erp_code
            and manual_mappings.get(record.mapping_key) == record.erp_code
        }

    def tax_not_required_source_rows(self, run_id: str) -> list[int]:
        run = self.get_run(run_id)
        return sorted(
            {
                issue.pointer.row
                for issue in run.unresolved_issues
                if issue.kind == "tax"
            }
        )

    def confirm_tax_not_required(
        self,
        run_id: str,
        source_rows: list[int],
    ) -> tuple[ProcessedRun, int]:
        run = self.get_run(run_id)
        if not isinstance(source_rows, list) or not source_rows:
            raise ValueError("Нет строк для применения решения по налогообложению")

        records_by_row: dict[int, list[PreviewRecord]] = {}
        for record in run.records:
            records_by_row.setdefault(record.source_row, []).append(record)
        eligible = set(self.tax_not_required_source_rows(run_id))
        validated: list[int] = []
        seen: set[int] = set()
        for raw_row in source_rows:
            try:
                source_row = int(raw_row)
            except (TypeError, ValueError) as exc:
                raise ValueError("Некорректная исходная строка") from exc
            if source_row in seen:
                continue
            seen.add(source_row)
            row_records = records_by_row.get(source_row)
            if not row_records:
                raise ValueError("Исходная строка не найдена")
            if source_row in eligible:
                validated.append(source_row)
                continue
            if all(record.tax == TAX_NOT_REQUIRED for record in row_records):
                continue
            raise ValueError("Строка больше не требует решения по налогообложению")

        for source_row in validated:
            self.correct_row(run_id, source_row, {"tax": TAX_NOT_REQUIRED})
        return run, len(validated)

    def _match_intalev_cfo(self, raw_value: str) -> tuple[IntalevCFO | None, str | None]:
        if not raw_value:
            return None, None
        matches = {
            item.source_key: item
            for item in self.intalev_cfos()
            if raw_value in {item.code, item.name, item.full_path}
        }
        if len(matches) == 1:
            return next(iter(matches.values())), None
        if len(matches) > 1:
            return None, "ЦФО Инталев неоднозначен в загруженном классификаторе"
        return None, "ЦФО Инталев отсутствует в загруженном классификаторе"

    def _initialize_cfo_mappings(self, run: ProcessedRun) -> None:
        for source_row in sorted({record.source_row for record in run.records}):
            row_records = [record for record in run.records if record.source_row == source_row]
            if not row_records:
                continue
            raw_value = row_records[0].source_cfo
            matched, _ = self._match_intalev_cfo(raw_value)
            source_key = matched.source_key if matched else ""
            for record in row_records:
                record.source_cfo = raw_value
                record.source_cfo_key = source_key
            self._rebuild_row_state(run, source_row)

    def cfo_mapping_entries(self, run_id: str) -> list[dict[str, Any]]:
        run = self.get_run(run_id)
        if not run.cfo_mapping_enabled:
            return []
        catalog = {item.source_key: item for item in self.intalev_cfos()}
        mappings = self.store.load_cfo_mappings()
        nodes = {node.node_id: node for node in self.organization_nodes()}

        grouped: dict[str, dict[str, Any]] = {}
        for record in run.records:
            if not record.source_cfo:
                continue
            group_key = (
                f"key:{record.source_cfo_key}"
                if record.source_cfo_key
                else f"raw:{record.source_cfo}"
            )
            group = grouped.setdefault(
                group_key,
                {
                    "source_key": record.source_cfo_key,
                    "raw_values": set(),
                    "source_rows": set(),
                },
            )
            group["raw_values"].add(record.source_cfo)
            group["source_rows"].add(record.source_row)

        result: list[dict[str, Any]] = []
        for group in grouped.values():
            source_key = str(group["source_key"])
            raw_values = sorted(group["raw_values"])
            raw_value = raw_values[0]
            source_rows = set(group["source_rows"])
            matched = catalog.get(source_key)
            target_node_id = mappings.get(source_key, "") if source_key else ""
            target = nodes.get(target_node_id)
            _, match_reason = self._match_intalev_cfo(raw_value)
            if source_key and target_node_id and target is None:
                status = "Сохранённый узел 1С отсутствует в текущем справочнике"
            elif source_key and target:
                status = "Сопоставление ЦФО подтверждено"
            elif source_key:
                status = "Требуется выбрать узел 1С"
            else:
                status = match_reason or "ЦФО Инталев не определён"
            result.append(
                {
                    "source_key": source_key,
                    "source_cfo": matched.name if matched else raw_value,
                    "source_label": matched.label if matched else raw_value,
                    "source_rows": sorted(source_rows),
                    "row_count": len(source_rows),
                    "target_node_id": target.node_id if target else "",
                    "target_label": (
                        f"{target.full_path} ({target.code})" if target else ""
                    ),
                    "confirmed": target is not None,
                    "eligible": bool(source_key),
                    "status": status,
                }
            )
        return sorted(result, key=lambda item: item["source_label"].casefold())

    def confirm_cfo_mappings(
        self,
        run_id: str,
        selections: list[dict[str, Any]],
    ) -> tuple[ProcessedRun, int]:
        run = self.get_run(run_id)
        if not run.cfo_mapping_enabled:
            raise ValueError("Сначала загрузите классификатор ЦФО Инталев")
        if not isinstance(selections, list) or not selections:
            raise ValueError("Нет заполненных сопоставлений ЦФО для подтверждения")

        entries = {
            item["source_key"]: item
            for item in self.cfo_mapping_entries(run_id)
            if item["source_key"] and item["eligible"]
        }
        nodes = {node.node_id: node for node in self.organization_nodes()}
        validated: dict[str, str] = {}
        for item in selections:
            if not isinstance(item, dict):
                raise ValueError("Список сопоставлений ЦФО заполнен некорректно")
            source_key = str(item.get("source_key") or "")
            target_node_id = str(item.get("target_node_id") or "")
            if not source_key or not target_node_id:
                raise ValueError("Одно из сопоставлений ЦФО заполнено не полностью")
            if source_key not in entries:
                raise ValueError("Исходный ЦФО отсутствует в текущем preview или неоднозначен")
            if target_node_id not in nodes:
                raise ValueError("Выбранный узел 1С отсутствует в текущем справочнике")
            previous = validated.get(source_key)
            if previous is not None and previous != target_node_id:
                raise ValueError("Один ЦФО Инталев нельзя сопоставить с двумя узлами 1С")
            validated[source_key] = target_node_id

        current = self.store.load_cfo_mappings()
        changed = {
            key: value
            for key, value in validated.items()
            if current.get(key) != value
        }
        self.store.save_cfo_mappings(changed)

        affected_rows = {
            record.source_row
            for record in run.records
            if record.source_cfo_key in validated
        }
        for source_row in sorted(affected_rows):
            self._rebuild_row_state(run, source_row)
        return run, len(changed)

    def confirm_filled_erp(
        self,
        run_id: str,
        selections: list[dict[str, Any]],
    ) -> tuple[ProcessedRun, int]:
        """Confirm explicit, already visible ERP selections for multiple source rows."""

        run = self.get_run(run_id)
        if not isinstance(selections, list) or not selections:
            raise ValueError("Нет полностью заполненных ERP-сопоставлений для подтверждения")

        records_by_row: dict[int, list[PreviewRecord]] = {}
        for record in run.records:
            records_by_row.setdefault(record.source_row, []).append(record)
        if len(selections) > len(records_by_row):
            raise ValueError("Список ERP-сопоставлений не соответствует текущему preview")

        editable_rows = {
            issue.pointer.row
            for issue in run.unresolved_issues
            if self._issue_is_inline_editable(issue)
        }
        catalog = {
            (article.expense_type, article.expense_group, article.source_article, article.code): article
            for article in self.erp_articles()
        }
        manual_mappings = self.store.load_manual_mappings()
        seen_rows: set[int] = set()
        codes_by_mapping_key: dict[tuple[str, str, str, str], str] = {}
        validated: list[tuple[int, str]] = []

        required = {
            "source_row",
            "expense_type",
            "expense_group",
            "source_article",
            "erp_code",
        }
        for item in selections:
            if not isinstance(item, dict) or not required.issubset(item):
                raise ValueError("Одно из ERP-сопоставлений заполнено не полностью")
            try:
                source_row = int(item["source_row"])
            except (TypeError, ValueError) as exc:
                raise ValueError("Некорректная исходная строка ERP-сопоставления") from exc
            if source_row in seen_rows:
                continue
            seen_rows.add(source_row)

            expense_type = str(item["expense_type"])
            expense_group = str(item["expense_group"])
            source_article = str(item["source_article"])
            erp_code = str(item["erp_code"])
            if not erp_code:
                raise ValueError("Одно из ERP-сопоставлений не содержит ERP-код")
            signature = (expense_type, expense_group, source_article, erp_code)
            if signature not in catalog:
                raise ValueError(
                    "Одно из ERP-сопоставлений больше не соответствует загруженному справочнику"
                )

            row_records = records_by_row.get(source_row)
            if not row_records:
                raise ValueError("Исходная строка ERP-сопоставления не найдена")
            base = row_records[0]
            already_confirmed = (
                base.erp_code == erp_code
                and manual_mappings.get(base.mapping_key) == erp_code
            )
            if source_row not in editable_rows and not already_confirmed:
                raise ValueError("Строка больше не доступна для массового подтверждения")

            previous_code = codes_by_mapping_key.get(base.mapping_key)
            if previous_code is not None and previous_code != erp_code:
                raise ValueError(
                    "Одинаковый исходный путь нельзя подтвердить с разными ERP-кодами"
                )
            codes_by_mapping_key[base.mapping_key] = erp_code
            validated.append((source_row, erp_code))

        if not validated:
            raise ValueError("Нет полностью заполненных ERP-сопоставлений для подтверждения")

        for source_row, erp_code in validated:
            self.correct_row(run_id, source_row, {"erp_code": erp_code})
        return run, len(validated)

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
            raise ValueError("Выберите хотя бы одно изменение")

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
            if original != selected:
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
            mapping_key = row_records[0].mapping_key
            if self.store.load_manual_mappings().get(mapping_key) != changes["erp_code"]:
                self.store.save_manual_mapping(mapping_key, changes["erp_code"])
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
            if issue.kind in {"tax", "erp-mapping", "cfo-mapping"}:
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
        source_cfo_value = base.source_cfo if run.cfo_mapping_enabled else base.cfo
        field_values = {
            "expense_type": base.expense_type,
            "department": base.department,
            "organization_type": base.organization_type,
            "cfo": source_cfo_value,
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

        if run.cfo_mapping_enabled and source_cfo_value:
            matched, match_reason = self._match_intalev_cfo(source_cfo_value)
            if matched:
                for record in row_records:
                    record.source_cfo_key = matched.source_key
                target_node_id = self.store.load_cfo_mappings().get(matched.source_key, "")
                nodes = {node.node_id: node for node in self.organization_nodes()}
                target = nodes.get(target_node_id)
                if target:
                    for record in row_records:
                        record.cfo = target.full_path
                        record.cfo_target_node_id = target.node_id
                        record.cfo_mapping_confirmed = True
                else:
                    for record in row_records:
                        record.cfo = source_cfo_value
                        record.cfo_target_node_id = ""
                        record.cfo_mapping_confirmed = False
                    if target_node_id:
                        cfo_reason = (
                            "Сохранённый узел 1С для ЦФО отсутствует в текущем справочнике"
                        )
                    else:
                        cfo_reason = "ЦФО Инталев не сопоставлен с узлом 1С"
                    dynamic_reasons.append(cfo_reason)
                    run.issues.append(
                        self._issue_from_record(
                            base,
                            "cfo-mapping",
                            cfo_reason,
                            "cfo",
                            source_cfo_value,
                        )
                    )
            else:
                for record in row_records:
                    record.source_cfo_key = ""
                    record.cfo = source_cfo_value
                    record.cfo_target_node_id = ""
                    record.cfo_mapping_confirmed = False
                cfo_reason = match_reason or "ЦФО Инталев не определён"
                dynamic_reasons.append(cfo_reason)
                run.issues.append(
                    self._issue_from_record(
                        base,
                        "cfo-mapping",
                        cfo_reason,
                        "cfo",
                        source_cfo_value,
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
            reasons = list(dict.fromkeys(common_reasons))
            if record.amount is None:
                skip_reason = monthly_issues.get(record.month, "Месячная запись не сформирована")
                pointer = record.pointers["amount"]
                reasons.append(f"{skip_reason} ({pointer.sheet}!{pointer.cell})")
                record.status = STATUS_SKIPPED
            else:
                if record.amount < 0:
                    reasons.append("Отрицательная сумма")
                record.status = STATUS_ATTENTION if reasons else STATUS_OK
            record.reasons = list(dict.fromkeys(reasons))

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
