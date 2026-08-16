from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from .indicator_resolvers import detect_indicator_type
from .models import (
    ERPArticle,
    IndicatorType,
    Issue,
    PreviewRecord,
    REPORT_TYPE_CODE,
    RunContext,
    STATUS_ATTENTION,
    STATUS_OK,
    STATUS_SKIPPED,
    TAX_NOT_REQUIRED,
    SourcePointer,
    SourceRow,
)

EXCEL_ERRORS = {"#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"}

SHARED_FIELDS = {
    "reporting_unit": "единица отчёта",
    "expense_type": "тип расходов",
    "department": "департамент",
    "organization_type": "вид организации",
    "cfo": "отдел / ЦФО",
    "expense_group": "группа расходов",
    "article": "статья",
}


def as_text(value: Any) -> str:
    return "" if value is None else str(value)


def normalize_tax(value: Any, allowed_values: set[str] | None = None) -> tuple[str, str | None]:
    allowed = allowed_values or {"БЕЗ НДС", "20%", "22%"}
    if value == TAX_NOT_REQUIRED:
        return TAX_NOT_REQUIRED, None
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
    def __init__(
        self,
        articles: list[ERPArticle],
        saved_mappings: dict[tuple[str, str, str, str], str] | None = None,
    ):
        self.articles = articles
        self.saved_mappings = saved_mappings or {}
        self.by_code = {article.code: article for article in articles}
        self.by_path: dict[tuple[str, str, str], list[ERPArticle]] = defaultdict(list)
        for article in articles:
            self.by_path[article.path].append(article)

    def resolve(
        self, expense_type: str, expense_group: str, source_article: str
    ) -> tuple[ERPArticle | None, str | None]:
        path = (expense_type, expense_group, source_article)
        exact = self.by_path.get(path, [])
        saved_code = self.saved_mappings.get(manual_mapping_key(*path))

        if saved_code:
            saved = self.by_code.get(saved_code)
            if not saved:
                return None, "Сохранённый ERP-код отсутствует в текущем справочнике"

            exact_codes = {article.code for article in exact}
            if len(exact) == 1 and exact[0].code != saved_code:
                return (
                    saved,
                    f"Сохранённое ручное соответствие {saved_code} "
                    f"конфликтует с точным ERP-кодом {exact[0].code}",
                )
            if len(exact) > 1 and saved_code not in exact_codes:
                return (
                    saved,
                    "Сохранённое ручное соответствие конфликтует "
                    "с текущими точными кандидатами ERP",
                )
            return saved, None

        if len(exact) == 1:
            return exact[0], None
        if len(exact) > 1:
            return None, "Точный путь соответствует нескольким ERP-кодам"
        return None, "Точное соответствие ERP не найдено"


def _amount(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise InvalidOperation
    return Decimal(str(value))


def _pointer(row: SourceRow, field: str, month: int | None = None) -> SourcePointer:
    source_key = f"month_{month}" if month else ("article" if field == "source_article" else field)
    cell = row.cells.get(source_key) or row.cells["article"]
    return SourcePointer(
        file_name=row.source_file,
        sheet=row.sheet,
        row=row.row_number,
        cell=cell,
        field=field,
        month=month,
    )


def _record_pointers(row: SourceRow, month: int) -> dict[str, SourcePointer]:
    pointers = {
        "reporting_unit": _pointer(row, "reporting_unit"),
        "expense_type": _pointer(row, "expense_type"),
        "department": _pointer(row, "department"),
        "organization_type": _pointer(row, "organization_type"),
        "cfo": _pointer(row, "cfo"),
        "tax": _pointer(row, "tax"),
        "expense_group": _pointer(row, "expense_group"),
        "source_article": _pointer(row, "source_article"),
        "amount": _pointer(row, "amount", month),
    }
    for field in (
        "indicator_type",
        "revenue_group",
        "formula_condition",
        "analytics",
        "nomenclature",
        "unit",
    ):
        if field in row.cells:
            pointers[field] = _pointer(row, field)
    return pointers


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
        try:
            indicator_type = detect_indicator_type(
                indicator_type=row.indicator_type,
                revenue_group=row.revenue_group,
                formula_condition=row.formula_condition,
                analytics=row.analytics,
                nomenclature=row.nomenclature,
                unit=row.unit,
            )
        except ValueError as exc:
            indicator_type = IndicatorType.EXPENSE
            type_reason = str(exc)
            shared_reasons.append(type_reason)
            issues.append(
                _issue(
                    row,
                    "indicator-type",
                    type_reason,
                    "indicator_type",
                    row.indicator_type,
                )
            )

        indicator_fields = {
            "indicator_type": indicator_type,
            "revenue_group": as_text(row.revenue_group),
            "formula_condition": as_text(row.formula_condition),
            "analytics": as_text(row.analytics),
            "nomenclature": as_text(row.nomenclature),
            "unit": as_text(row.unit),
        }

        for field, value in shared.items():
            if value == "":
                reason = f"Не заполнено поле: {SHARED_FIELDS[field]}"
                shared_reasons.append(reason)
                issue_field = "source_article" if field == "article" else field
                issues.append(_issue(row, "shared-field", reason, issue_field, value))

        source_reporting_unit = shared["reporting_unit"]
        if source_reporting_unit and source_reporting_unit != context.reporting_unit:
            reason = (
                f"Единица отчёта в Excel «{source_reporting_unit}» "
                f"не совпадает с выбранной «{context.reporting_unit}»"
            )
            shared_reasons.append(reason)
            issues.append(
                _issue(
                    row,
                    "context-reporting-unit",
                    reason,
                    "reporting_unit",
                    source_reporting_unit,
                )
            )

        tax, tax_reason = normalize_tax(row.tax, allowed_tax_values)
        if tax_reason:
            shared_reasons.append(tax_reason)
            issues.append(_issue(row, "tax", tax_reason, "tax", row.tax))

        mapped, mapping_reason = mapper.resolve(
            shared["expense_type"], shared["expense_group"], shared["article"]
        )
        if mapping_reason:
            shared_reasons.append(mapping_reason)
            issues.append(
                _issue(row, "erp-mapping", mapping_reason, "source_article", row.article)
            )

        if not context.scenario_erp_confirmed:
            shared_reasons.append("Сценарий не подтверждён справочником ERP")

        for month, raw_amount in enumerate(row.months, start=1):
            pointers = _record_pointers(row, month)
            skip_reason: str | None = None
            if as_text(raw_amount) in EXCEL_ERRORS:
                skip_reason = "Ошибка Excel в месячной ячейке"
            else:
                try:
                    amount = _amount(raw_amount)
                except (InvalidOperation, ValueError):
                    amount = None
                    skip_reason = "Месячное значение не является числом"

            if skip_reason:
                issues.append(
                    _issue(
                        row,
                        "monthly-error",
                        skip_reason,
                        "amount",
                        raw_amount,
                        month,
                    )
                )
                records.append(
                    PreviewRecord(
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
                        amount=None,
                        source_reporting_unit=source_reporting_unit,
                        source_cfo=shared["cfo"],
                        status=STATUS_SKIPPED,
                        reasons=[
                            *shared_reasons,
                            f"{skip_reason} ({pointers['amount'].sheet}!{pointers['amount'].cell})",
                        ],
                        pointers=pointers,
                        **indicator_fields,
                    )
                )
                continue

            reasons = list(shared_reasons)
            if amount < 0:
                reasons.append("Отрицательная сумма")
                issues.append(
                    _issue(
                        row,
                        "negative-amount",
                        "Отрицательная сумма",
                        "amount",
                        raw_amount,
                        month,
                    )
                )

            records.append(
                PreviewRecord(
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
                    source_reporting_unit=source_reporting_unit,
                    source_cfo=shared["cfo"],
                    status=STATUS_ATTENTION if reasons else STATUS_OK,
                    reasons=reasons,
                    pointers=pointers,
                    **indicator_fields,
                )
            )

    return records, _deduplicate_shared_issues(issues)


def _issue(
    row: SourceRow,
    kind: str,
    description: str,
    field: str,
    raw_value: Any,
    month: int | None = None,
) -> Issue:
    return Issue(
        issue_id=uuid4().hex,
        kind=kind,
        description=description,
        pointer=_pointer(row, field, month),
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
