from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


REPORT_TYPE_NAME = "Отчет о прибылях и убытках"
REPORT_TYPE_CODE = "ОтчетОПрибыляхИУбытках"

STATUS_OK = "ОК"
STATUS_ATTENTION = "Требует внимания"
STATUS_SKIPPED = "Пропущено"
TAX_NOT_REQUIRED = "Не требуется"

MONTH_NAMES = (
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)


@dataclass(frozen=True)
class SourcePointer:
    file_name: str
    sheet: str
    row: int
    cell: str
    field: str
    month: int | None = None


@dataclass(frozen=True)
class CandidateRange:
    candidate_id: str
    sheet: str
    header_row: int
    first_data_row: int
    last_data_row: int
    columns: dict[str, int]
    source_kind: str = "prepared_budget"
    source_cfo: str = ""
    source_year: int | None = None

    @property
    def label(self) -> str:
        return f"{self.sheet}: строки {self.first_data_row}–{self.last_data_row}"


@dataclass(frozen=True)
class SourceRow:
    source_file: str
    sheet: str
    row_number: int
    reporting_unit: Any
    expense_type: Any
    department: Any
    organization_type: Any
    cfo: Any
    tax: Any
    expense_group: Any
    article: Any
    months: tuple[Any, ...]
    cells: dict[str, str]


@dataclass(frozen=True)
class ERPArticle:
    code: str
    name: str
    expense_type: str
    expense_group: str
    source_article: str

    @property
    def path(self) -> tuple[str, str, str]:
        return (self.expense_type, self.expense_group, self.source_article)


@dataclass(frozen=True)
class OrganizationNode:
    node_id: str
    code: str
    name: str
    parent_id: str | None
    full_path: str


@dataclass(frozen=True)
class IntalevCFO:
    source_key: str
    code: str
    name: str
    full_path: str = ""

    @property
    def label(self) -> str:
        identity = " · ".join(part for part in (self.code, self.name) if part)
        if self.full_path and self.full_path != self.name:
            return f"{identity} · {self.full_path}" if identity else self.full_path
        return identity or self.full_path


@dataclass(frozen=True)
class ArticleIndicatorRule:
    erp_code: str
    article_path: str
    article_name: str
    indicator: str
    sales_channel: str


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    year: int
    erp_code: str | None = None
    comment: str = ""
    erp_confirmed: bool = False

    @property
    def marker(self) -> str:
        return "" if self.erp_confirmed else "Не подтверждён справочником ERP"


@dataclass(frozen=True)
class RunContext:
    reporting_unit: str
    organization_node_id: str
    organization_name: str
    scenario_id: str
    scenario_name: str
    scenario_year: int
    scenario_erp_confirmed: bool
    year: int
    selected_months: tuple[int, ...] = ()


@dataclass
class PreviewRecord:
    record_id: str
    source_row: int
    month: int
    year: int
    reporting_unit: str
    organization: str
    scenario: str
    department: str
    organization_type: str
    cfo: str
    expense_type: str
    expense_group: str
    source_article: str
    erp_code: str
    erp_article_name: str
    tax: str
    amount: Decimal | None
    status: str = STATUS_OK
    reasons: list[str] = field(default_factory=list)
    pointers: dict[str, SourcePointer] = field(default_factory=dict)
    source_cfo: str = ""
    source_cfo_key: str = ""
    cfo_target_node_id: str = ""
    cfo_mapping_confirmed: bool = False
    indicator: str = ""
    sales_channel: str = ""
    indicator_match_status: str = ""
    indicator_match_reason: str = ""

    @property
    def comment(self) -> str:
        return "; ".join(dict.fromkeys(self.reasons))

    @property
    def month_name(self) -> str:
        return MONTH_NAMES[self.month - 1]

    @property
    def mapping_key(self) -> tuple[str, str, str, str]:
        return (REPORT_TYPE_CODE, self.expense_type, self.expense_group, self.source_article)

    @property
    def tax_not_required(self) -> bool:
        return self.tax == TAX_NOT_REQUIRED


@dataclass
class Issue:
    issue_id: str
    kind: str
    description: str
    pointer: SourcePointer
    reporting_unit: str = ""
    department: str = ""
    cfo: str = ""
    expense_type: str = ""
    expense_group: str = ""
    article: str = ""
    raw_value: str = ""
    resolved: bool = False


@dataclass
class ProcessedRun:
    run_id: str
    context: RunContext
    source_file: str
    candidate: CandidateRange
    records: list[PreviewRecord]
    issues: list[Issue]
    created_at: str
    rerun_count: int = 0
    cfo_mapping_enabled: bool = False
    indicator_classifier_loaded: bool = False

    def visible_records(self) -> list[PreviewRecord]:
        if not self.context.selected_months:
            return self.records
        selected = set(self.context.selected_months)
        return [record for record in self.records if record.month in selected]

    @property
    def unresolved_issues(self) -> list[Issue]:
        return [issue for issue in self.issues if not issue.resolved]
