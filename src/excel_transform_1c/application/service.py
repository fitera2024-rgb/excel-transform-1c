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
    article_indicator_rules,
    erp_articles,
    intalev_cfos,
    organization_nodes,
    parse_reference_workbook,
)
from excel_transform_1c.core.access import effective_organization_nodes
from excel_transform_1c.core.indicator_matching import (
    INDICATOR_AMBIGUOUS,
    INDICATOR_INCOMPLETE,
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
    apply_indicator_match,
)
from excel_transform_1c.baselines import baseline_counts
from excel_transform_1c.core.indicator_resolvers import IndicatorResolverEngine
from excel_transform_1c.core.models import (
    ArticleIndicatorRule,
    CandidateRange,
    ERPArticle,
    IntalevCFO,
    IndicatorType,
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
from excel_transform_1c.core.organization_hierarchy import (
    MISSING_ERP_ELEMENT_CODE_REASON,
    ExactOrganizationHierarchyResolver,
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
        packaged = baseline_counts()
        return {
            "erp_articles": len(self.store.load_reference("erp_articles")),
            "organizations": len(self.store.load_reference("organizations")),
            "scenarios": len(self.store.list_scenarios()),
            "intalev_cfos": len(self.store.load_reference("intalev_cfos")),
            "article_indicators": len(
                self.store.load_reference("article_indicators")
            ),
            "opiu_formulas": packaged["opiu_formulas"],
            "opiu_analytics": packaged["opiu_analytics"],
            "regions": packaged["regions"],
            "sales_networks": packaged["sales_networks"],
            "opiu_report_indicators": packaged["opiu_report_indicators"],
            "opiu_source_rules": packaged["opiu_source_rules"],
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

    def article_indicator_rules(self) -> list[ArticleIndicatorRule]:
        return article_indicator_rules(
            self.store.load_reference("article_indicators")
        )

    def upload_indicator_classifier(self, content: bytes, run_id: str | None = None) -> int:
        run = self.get_run(run_id) if run_id is not None else None
        payload = parse_reference_workbook(content, "article_indicators")
        self.store.replace_reference("article_indicators", payload)
        if run is not None:
            self._apply_indicator_matches(run)
        return len(payload)

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
            indicator_classifier_loaded=bool(self.article_indicator_rules()),
        )
        if run.cfo_mapping_enabled:
            self._initialize_cfo_mappings(run)
        self._apply_organization_reference_enrichment(run)
        self._apply_indicator_matches(run)
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

    def _apply_indicator_matches(
        self,
        run: ProcessedRun,
        source_rows: set[int] | None = None,
    ) -> None:
        rules = self.article_indicator_rules()
        engine = IndicatorResolverEngine(rules)
        run.indicator_classifier_loaded = bool(rules)
        for record in run.records:
            if source_rows is not None and record.source_row not in source_rows:
                continue
            previous_reason = record.indicator_match_reason
            match = engine.resolve(record)
            apply_indicator_match(record, match)
            if (
                match.status == INDICATOR_INCOMPLETE
                and match.rule is not None
                and match.rule.indicator.strip()
            ):
                # Keep the proven business result visible while the missing
                # output dimension remains attention-only and non-exportable.
                record.indicator = match.rule.indicator
                record.sales_channel = match.rule.sales_channel
            if record.indicator_type != IndicatorType.EXPENSE:
                if previous_reason:
                    record.reasons = [
                        reason for reason in record.reasons if reason != previous_reason
                    ]
                if match.status != INDICATOR_MATCHED and match.reason:
                    record.reasons.append(match.reason)
                if record.status != STATUS_SKIPPED:
                    record.status = STATUS_ATTENTION if record.reasons else STATUS_OK

    def indicator_counts(self, run_id: str) -> dict[str, int]:
        run = self.get_run(run_id)
        statuses = {
            record.source_row: record.indicator_match_status
            for record in run.records
        }
        return {
            "automatic": sum(status == INDICATOR_MATCHED for status in statuses.values()),
            "attention": sum(
                status in {
                    INDICATOR_AMBIGUOUS,
                    INDICATOR_INCOMPLETE,
                    INDICATOR_MISSING,
                }
                for status in statuses.values()
            ),
            "not_found": sum(status == INDICATOR_MISSING for status in statuses.values()),
        }

    def indicator_unresolved_rows(self, run_id: str) -> list[dict[str, Any]]:
        run = self.get_run(run_id)
        by_row: dict[int, PreviewRecord] = {}
        for record in run.records:
            by_row.setdefault(record.source_row, record)
        labels = {INDICATOR_MISSING: "Не найдено", INDICATOR_AMBIGUOUS: "Неоднозначно", INDICATOR_INCOMPLETE: "Правило заполнено не полностью"}
        result: list[dict[str, Any]] = []
        for source_row, record in sorted(by_row.items()):
            status = record.indicator_match_status
            if status not in labels:
                continue
            pointer = record.pointers.get("source_article")
            result.append({
                "source_row": source_row,
                "source_line": f"{pointer.sheet if pointer else run.candidate.sheet}!{source_row}",
                "expense_type": record.expense_type or "Без типа",
                "expense_group": record.expense_group or "Без группы",
                "source_article": record.source_article or "Без статьи",
                "indicator_type": record.indicator_type_label,
                "indicator": record.indicator,
                "sales_channel": record.sales_channel,
                "erp_code": record.erp_code,
                "status": labels[status],
                "reason": record.indicator_match_reason,
                "action": (
                    "Дополнить точную связь значением канала сбыта"
                    if record.indicator and not record.sales_channel
                    else "Загрузить / дополнить классификатор"
                ),
            })
        return result

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
        return None, None

    def _resolve_intalev_cfo(self, reporting_unit: str, raw_value: str) -> tuple[IntalevCFO | None, str | None]:
        direct, direct_reason = self._match_intalev_cfo(raw_value)
        if direct or direct_reason:
            return direct, direct_reason
        if not raw_value:
            return None, None
        catalog = {item.source_key: item for item in self.intalev_cfos()}
        saved_key = self.store.load_source_cfo_mappings().get((reporting_unit, raw_value), "")
        if saved_key:
            saved = catalog.get(saved_key)
            if saved:
                return saved, None
            return None, "Сохранённый ЦФО Инталев отсутствует в текущем классификаторе"
        return None, "Исходный ЦФО не сопоставлен с ЦФО Инталев"

    @staticmethod
    def _record_source_cfo_identity(run: ProcessedRun, record: PreviewRecord) -> tuple[str, str]:
        return (record.source_reporting_unit or run.context.reporting_unit, record.source_cfo)

    def _initialize_cfo_mappings(self, run: ProcessedRun) -> None:
        for source_row in sorted({record.source_row for record in run.records}):
            row_records = [record for record in run.records if record.source_row == source_row]
            if not row_records:
                continue
            base = row_records[0]
            reporting_unit, raw_value = self._record_source_cfo_identity(run, base)
            if not raw_value:
                for record in row_records:
                    record.source_reporting_unit = reporting_unit
                continue
            matched, _ = self._resolve_intalev_cfo(reporting_unit, raw_value)
            source_key = matched.source_key if matched else ""
            for record in row_records:
                record.source_reporting_unit = reporting_unit
                record.source_cfo = raw_value
                record.source_cfo_key = source_key
            self._rebuild_row_state(run, source_row)

    def cfo_mapping_entries(self, run_id: str) -> list[dict[str, Any]]:
        run = self.get_run(run_id)
        if not run.cfo_mapping_enabled:
            return []
        mappings = self.store.load_cfo_mappings()
        nodes = {node.node_id: node for node in self.organization_nodes()}
        grouped: dict[tuple[str, str], set[int]] = {}
        for record in run.records:
            reporting_unit, raw_value = self._record_source_cfo_identity(run, record)
            if raw_value:
                grouped.setdefault((reporting_unit, raw_value), set()).add(record.source_row)
        result: list[dict[str, Any]] = []
        for (reporting_unit, raw_value), source_rows in grouped.items():
            matched, match_reason = self._resolve_intalev_cfo(reporting_unit, raw_value)
            key = matched.source_key if matched else ""
            target_node_id = mappings.get(key, "") if matched else ""
            target = nodes.get(target_node_id)
            if matched and target_node_id and target is None:
                status = "Сохранённый узел 1С отсутствует в текущем справочнике"
            elif matched and target:
                status = "Сопоставление ЦФО подтверждено"
            elif matched:
                status = "ЦФО Инталев выбран; требуется выбрать узел 1С"
            else:
                status = match_reason or "Выберите ЦФО Инталев"
            identity = f"{reporting_unit}\0{raw_value}"
            result.append({
                "entry_key": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
                "source_key": key,
                "intalev_source_key": key,
                "source_reporting_unit": reporting_unit,
                "source_cfo": raw_value,
                "source_label": f"{reporting_unit} · {raw_value}" if reporting_unit else raw_value,
                "intalev_label": matched.label if matched else "",
                "source_rows": sorted(source_rows),
                "row_count": len(source_rows),
                "target_node_id": target.node_id if target else "",
                "target_label": f"{target.full_path} ({target.code})" if target else "",
                "confirmed": target is not None,
                "intalev_confirmed": matched is not None,
                "eligible": True,
                "status": status,
            })
        return sorted(result, key=lambda item: item["source_label"].casefold())

    def confirm_cfo_mappings(self, run_id: str, selections: list[dict[str, Any]]) -> tuple[ProcessedRun, int]:
        run = self.get_run(run_id)
        if not run.cfo_mapping_enabled:
            raise ValueError("Сначала загрузите классификатор ЦФО Инталев")
        if not isinstance(selections, list) or not selections:
            raise ValueError("Нет заполненных сопоставлений ЦФО для подтверждения")
        catalog = {item.source_key: item for item in self.intalev_cfos()}
        nodes = {node.node_id: node for node in self.organization_nodes()}
        entries = {(item["source_reporting_unit"], item["source_cfo"]): item for item in self.cfo_mapping_entries(run_id)}
        source_changes: dict[tuple[str, str], str] = {}
        target_changes: dict[str, str] = {}
        affected: set[tuple[str, str]] = set()
        old_direct: set[str] = set()
        for item in selections:
            if not isinstance(item, dict):
                raise ValueError("Список сопоставлений ЦФО заполнен некорректно")
            ru = str(item.get("source_reporting_unit") or "")
            raw = str(item.get("source_cfo") or "")
            key = str(item.get("intalev_source_key") or item.get("source_key") or "")
            target = str(item.get("target_node_id") or "")
            if not ru and not raw:
                if not key or not target:
                    raise ValueError("Одно из сопоставлений ЦФО заполнено не полностью")
                if key not in catalog:
                    raise ValueError("ЦФО Инталев отсутствует в текущем классификаторе")
                if target not in nodes:
                    raise ValueError("Выбранный узел 1С отсутствует в текущем справочнике")
                if key in target_changes and target_changes[key] != target:
                    raise ValueError("Один ЦФО Инталев нельзя сопоставить с двумя узлами 1С")
                target_changes[key] = target
                old_direct.add(key)
                continue
            if not ru or not raw:
                raise ValueError("Не указан исходный ЦФО и единица отчёта")
            if (ru, raw) not in entries:
                raise ValueError("Исходный ЦФО отсутствует в текущем preview")
            if key not in catalog:
                raise ValueError("Выберите ЦФО Инталев из текущего классификатора")
            if target not in nodes:
                raise ValueError("Выберите точный узел 1С из текущего дерева")
            identity = (ru, raw)
            if identity in source_changes and source_changes[identity] != key:
                raise ValueError("Один исходный ЦФО нельзя сопоставить с двумя ЦФО Инталев")
            if key in target_changes and target_changes[key] != target:
                raise ValueError("Один ЦФО Инталев нельзя сопоставить с двумя узлами 1С")
            source_changes[identity] = key
            target_changes[key] = target
            affected.add(identity)
        current_source = self.store.load_source_cfo_mappings()
        current_targets = self.store.load_cfo_mappings()
        self.store.save_source_cfo_mappings({i: k for i, k in source_changes.items() if current_source.get(i) != k})
        self.store.save_cfo_mappings({k: v for k, v in target_changes.items() if current_targets.get(k) != v})
        affected_rows = {record.source_row for record in run.records if self._record_source_cfo_identity(run, record) in affected or record.source_cfo_key in old_direct}
        for source_row in sorted(affected_rows):
            self._rebuild_row_state(run, source_row)
        return run, len(affected or old_direct)

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
            source_reporting_unit = base.source_reporting_unit or run.context.reporting_unit
            matched, match_reason = self._resolve_intalev_cfo(source_reporting_unit, source_cfo_value)
            if matched:
                for record in row_records:
                    record.source_reporting_unit = source_reporting_unit
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
                    record.source_reporting_unit = source_reporting_unit
                    record.source_cfo_key = ""
                    record.cfo = source_cfo_value
                    record.cfo_target_node_id = ""
                    record.cfo_mapping_confirmed = False
                cfo_reason = match_reason or "Исходный ЦФО не сопоставлен с ЦФО Инталев"
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

        self._apply_organization_reference_enrichment(run, {source_row})
        self._apply_indicator_matches(run, {source_row})

    def _apply_organization_reference_enrichment(
        self,
        run: ProcessedRun,
        source_rows: set[int] | None = None,
    ) -> None:
        nodes = self.organization_nodes()
        resolver = ExactOrganizationHierarchyResolver(nodes)
        selected_rows = source_rows or {record.source_row for record in run.records}

        for source_row in sorted(selected_rows):
            row_records = [
                record for record in run.records if record.source_row == source_row
            ]
            if not row_records:
                continue
            for issue in run.issues:
                if (
                    not issue.resolved
                    and issue.kind == "organization-reference"
                    and issue.pointer.row == source_row
                ):
                    issue.resolved = True

            base = row_records[0]
            resolution = resolver.resolve(
                run.context.organization_node_id,
                base.department,
                base.source_cfo or base.cfo,
            )
            reason = resolution.reason if resolution else None
            for record in row_records:
                record.organization_unit = resolution.organization_unit if resolution else ""
                record.organization_unit_code = (
                    resolution.organization_unit_code if resolution else ""
                )
                record.erp_department = resolution.department if resolution else ""
                record.cfo_code = resolution.cfo_code if resolution else ""
                record.reasons = [
                    item
                    for item in record.reasons
                    if item != MISSING_ERP_ELEMENT_CODE_REASON
                ]
                if reason:
                    record.reasons.append(reason)
                if record.status != STATUS_SKIPPED:
                    record.status = STATUS_ATTENTION if record.reasons else STATUS_OK

            if reason:
                run.issues.append(
                    self._issue_from_record(
                        base,
                        "organization-reference",
                        reason,
                        "department",
                        base.department,
                    )
                )

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
             reporting_unit=record.source_reporting_unit or record.reporting_unit,
            department=record.department,
            cfo=record.cfo,
            expense_type=record.expense_type,
            expense_group=record.expense_group,
            article=record.source_article,
            raw_value="" if raw_value is None else str(raw_value),
        )

    def export_run(self, run_id: str) -> bytes:
        return export_opiu_light(self.get_run(run_id).visible_records())
