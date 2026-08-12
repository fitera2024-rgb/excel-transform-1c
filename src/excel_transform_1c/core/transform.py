from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from .models import (
    ERPArticle,
    Issue,
    PreviewRecord,
    REPORT_TYPE_CODE,
    RunContext,
    STATUS_ATTENTION,
    STATUS_OK,
    STATUS_SKIPPED,
    SourcePointer,
    SourceRow,
)

EXCEL_ERRORS = {"#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"}


def as_text(value: Any) -> str:
    return "" if value is None else str(value)


def normalize_tax(value: Any, allowed_values: set[str] | None = None) -> tuple[str, str | None]:
    allowed = allowed_values or {"БЕЗ НДС", "20%", "22%"}
    if value is None or value == "?" or value == "":
        return "", "Налогообложение не определено"
    if isinstance(value, bool):
        return as_text(value), "Налогообложение не определено"
    if isinstance(value, (int, float, Decimal)):
        numeric = Decimal(str(value))
        if numeric == Decimal("0"):
            return "", "Числовой 0 по налогообложению неоднозначен"
        if numeric == Decimal("0.2"):
            return "20%", None
        if numeric == Decimal("0.22"):
            return "22%", None
    text = as_text(value)
    if text in allowed:
        return text, None
    return text, "Налогообложение отсутствует в утверждённом справочнике"


def manual_mapping_key(expense_type: str, expense_group: str, article: str) -> tuple[str, str, str, str]:
    return (REPORT_TYPE_CODE, expense_type, expense_group, article)


class ExactERPMapper:
    def __init__(self, articles: list[ERPArticle], saved_mappings: dict[tuple[str, str, str, str], str] | None = None):
        self.articles = articles
        self.saved_mappings = saved_mappings or {}
        self.by_code = {article.code: article for article in articles}
        self.by_path: dict[tuple[str, str, str], list[ERPArticle]] = defaultdict(list)
        for article in articles:
            self.by_path[article.path].append(article)

    def resolve(self, expense_type: str, expense_group: str, source_article: str) -> tuple[ERPArticle | None, str | None]:
        path = (expense_type, expense_group, source_article)
        exact = self.by_path.get(path, [])
        saved_code = self.saved_mappings.get(manual_mapping_key(*path))
        if len(exact) == 1:
            if saved_code and saved_code != exact[0].code:
                return None, "Сохранённое ручное соответствие конфликтует с точным ERP-путём"
            return exact[0], None
        if len(exact) > 1:
            return None, "Точный путь соответствует нескольким ERP-кодам"

        if saved_code:
            saved = self.by_code.get(saved_code)
            if saved:
                return saved, None
            return None, "Сохранённое соответствие конфликтует с текущей иерархией"
        return None, "Точное соответствие ERP не найдено"


def _amount(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise InvalidOperation
    return Decimal(str(value))


def _pointer(row: SourceRow, field: str, month: int | None = None) -> SourcePointer:
    key = f"month_{month}" if month else field
    return SourcePointer(
        file_name=row.source_file,
        sheet=row.sheet,
        row=row.row_number,
        cell=row.cells[key],
        field=field,
        month=month,
    )


def transform_rows(
    rows: list[SourceRow],
    context: RunContext,
    mapper: ExactERPMapper,
    allowed_tax_values: set[str] | None = None,
) -> tuple[list[PreviewRecord], list[Issue]]:
    records: list[PreviewRecord] = []
    issues: list[Issue] = []
    for row in rows:
        shared = {
            "reporting_unit": as_text(row.reporting_unit),
            "expense_type": as_text(row.expense_type),
            "department": as_text(row.department),
            "organization_type": as_text(row.organization_type),
            "cfo": as_text(row.cfo),
            "expense_group": as_text(row.expense_group),
            "article": as_text(row.article),
        }
        shared_reasons: list[str] = []
        for field, value in shared.items():
            if value == "":
                reason = f"Не заполнено поле: {field}"
                shared_reasons.append(reason)
                issues.append(_issue(row, "shared-field", reason, field, value))

        source_reporting_unit = shared["reporting_unit"]
        if source_reporting_unit and source_reporting_unit != context.reporting_unit:
            reason = (
                f"Единица отчёта в Excel «{source_reporting_unit}» не совпадает "
                f"с выбранной «{context.reporting_unit}»"
            )
            shared_reasons.append(reason)
            issues.append(_issue(row, "context-conflict", reason, "reporting_unit", row.reporting_unit))

        tax, tax_reason = normalize_tax(row.tax, allowed_tax_values)
        if tax_reason:
            shared_reasons.append(tax_reason)
            issues.append(_issue(row, "tax", tax_reason, "tax", row.tax))

        mapped, mapping_reason = mapper.resolve(shared["expense_type"], shared["expense_group"], shared["article"])
        if mapping_reason:
            shared_reasons.append(mapping_reason)
            issues.append(_issue(row, "erp-mapping", mapping_reason, "article", row.article))

        if not context.scenario_erp_confirmed:
            shared_reasons.append("Сценарий не подтверждён справочником ERP")

        for month, raw_amount in enumerate(row.months, start=1):
            pointers = {
                field: _pointer(row, field)
                for field in (
                    "reporting_unit",
                    "department",
                    "cfo",
                    "tax",
                    "expense_group",
                    "article",
                )
            }
            pointers["amount"] = _pointer(row, f"month_{month}", month)
            if as_text(raw_amount) in EXCEL_ERRORS:
                reason = "Ошибка Excel в месячной ячейке"
                issues.append(_issue(row, "monthly-error", reason, f"month_{month}", raw_amount, month))
                records.append(
                    _record(
                        row,
                        context,
                        shared,
                        tax,
                        mapped,
                        month,
                        None,
                        STATUS_SKIPPED,
                        [*shared_reasons, reason],
                        pointers,
                    )
                )
                continue
            try:
                amount = _amount(raw_amount)
            except (InvalidOperation, ValueError):
                reason = "Месячное значение не является числом"
                issues.append(_issue(row, "monthly-error", reason, f"month_{month}", raw_amount, month))
                records.append(
                    _record(
                        row,
                        context,
                        shared,
                        tax,
                        mapped,
                        month,
                        None,
                        STATUS_SKIPPED,
                        [*shared_reasons, reason],
                        pointers,
                    )
                )
                continue
            reasons = list(shared_reasons)
            if amount < 0:
                reasons.append("Отрицательная сумма")
                issues.append(_issue(row, "negative-amount", "Отрицательная сумма", f"month_{month}", raw_amount, month))
            records.append(
                _record(
                    row,
                    context,
                    shared,
                    tax,
                    mapped,
                    month,
                    amount,
                    STATUS_ATTENTION if reasons else STATUS_OK,
                    reasons,
                    pointers,
                )
            )
    return records, _deduplicate_shared_issues(issues)


def _record(
    row: SourceRow,
    context: RunContext,
    shared: dict[str, str],
    tax: str,
    mapped: ERPArticle | None,
    month: int,
    amount: Decimal | None,
    status: str,
    reasons: list[str],
    pointers: dict[str, SourcePointer],
) -> PreviewRecord:
    return PreviewRecord(
        record_id=uuid4().hex,
        source_row=row.row_number,
        month=month,
        year=context.year,
        reporting_unit=context.reporting_unit,
        organization=context.organization_name,
        scenario=context.scenario_name,
        department=shared["department"],
        organization_type=shared["organization_type"],
        cfo=shared["cfo"],
        expense_type=shared["expense_type"],
        expense_group=shared["expense_group"],
        source_article=shared["article"],
        erp_code=mapped.code if mapped else "",
        erp_article_name=mapped.name if mapped else "",
        tax=tax,
        amount=amount,
        status=status,
        reasons=reasons,
        pointers=pointers,
    )


def _issue(
    row: SourceRow,
    kind: str,
    description: str,
    field: str,
    raw_value: Any,
    month: int | None = None,
) -> Issue:
    pointer_field = field if not field.startswith("month_") else field
    return Issue(
        issue_id=uuid4().hex,
        kind=kind,
        description=description,
        pointer=_pointer(row, pointer_field, month),
        reporting_unit=as_text(row.reporting_unit),
        department=as_text(row.department),
        cfo=as_text(row.cfo),
        expense_type=as_text(row.expense_type),
        expense_group=as_text(row.expense_group),
        article=as_text(row.article),
        raw_value=as_text(raw_value),
    )


def _deduplicate_shared_issues(issues: list[Issue]) -> list[Issue]:
    seen: set[tuple[Any, ...]] = set()
    result: list[Issue] = []
    for issue in issues:
        key = (
            issue.kind,
            issue.pointer.file_name,
            issue.pointer.sheet,
            issue.pointer.row,
            issue.pointer.cell,
            issue.description,
        )
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result
