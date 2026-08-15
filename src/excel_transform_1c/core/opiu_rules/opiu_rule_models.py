from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


AUTO_MATCH = "AUTO_MATCH"
NOT_FOUND = "NOT_FOUND"
AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class FormulaInputRow:
    source_row: int
    name: str
    formula: str
    indent: int = 0
    measure: str = "Сумма"


@dataclass(frozen=True)
class AnalyticInputRow:
    source_row: int
    name: str
    analytics: tuple[str, ...]
    indent: int = 0


@dataclass(frozen=True)
class OPIUFormulaRule:
    source_row: int
    report_line: str
    report_indicator: str
    disclosure_group: str
    article: str
    formula: str
    formula_condition: str
    source_tokens: tuple[str, ...]
    measure: str = "Сумма"


@dataclass(frozen=True)
class OPIUAnalyticRule:
    source_row: int
    report_indicator: str
    required_analytics: tuple[str, ...]
    organization_required: bool = False
    region_required: bool = False
    network_required: bool = False
    cfo_required: bool = False


@dataclass(frozen=True)
class ERPIndicatorCatalogEntry:
    indicator_code: str
    name: str
    report_line: str
    indicator_group: str
    column: str = ""
    normalized_code: str = ""


@dataclass(frozen=True)
class FormulaPredicate:
    field: str
    expected: str


@dataclass(frozen=True)
class ERPSourceRule:
    formula_code: str
    name: str
    description: str
    source: str
    register: str
    account: str
    corresponding_account: str
    consumer: str
    method: str
    code: str
    formula_condition: str
    disclosure_groups: tuple[str, ...] = ()
    predicates: tuple[FormulaPredicate, ...] = ()


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    name: str


@dataclass(frozen=True)
class OPIURule:
    rule_id: str
    report_line: str
    report_indicator: str
    disclosure_group: str
    article: str
    article_code: str
    source: str
    formula_condition: str
    required_analytics: tuple[str, ...]
    region_required: bool
    network_required: bool
    cfo_required: bool
    organization_required: bool = False
    indicator_code: str = ""
    indicator_group: str = ""
    sales_channel: str = ""
    predicates: tuple[FormulaPredicate, ...] = ()


@dataclass(frozen=True)
class UnresolvedRule:
    disclosure_group: str
    article: str
    reason: str
    required: str


@dataclass(frozen=True)
class OPIURuleCatalog:
    formula_rules: tuple[OPIUFormulaRule, ...]
    analytic_rules: tuple[OPIUAnalyticRule, ...]
    indicator_catalog: tuple[ERPIndicatorCatalogEntry, ...]
    source_rules: tuple[ERPSourceRule, ...]
    region_catalog: tuple[CatalogEntry, ...]
    network_catalog: tuple[CatalogEntry, ...]
    rules: tuple[OPIURule, ...]
    unresolved: tuple[UnresolvedRule, ...]


@dataclass(frozen=True)
class OPIUMatchResult:
    status: str
    rule: OPIURule | None = None
    reason: str = ""


@dataclass(frozen=True)
class OPIUResolutionContext:
    disclosure_group: str
    article: str
    article_code: str = ""
    organization: str = ""
    cfo: str = ""
    region: str = ""
    network: str = ""
    nomenclature: str = ""
    analytics: dict[str, str] = field(default_factory=dict, compare=False, hash=False)


def opiu_rule_to_payload(rule: OPIURule) -> dict[str, Any]:
    return asdict(rule)


def opiu_rule_from_payload(payload: dict[str, Any]) -> OPIURule:
    predicates = tuple(
        item if isinstance(item, FormulaPredicate) else FormulaPredicate(**item)
        for item in payload.get("predicates", ())
    )
    return OPIURule(
        rule_id=str(payload.get("rule_id") or ""),
        report_line=str(payload.get("report_line") or ""),
        report_indicator=str(payload.get("report_indicator") or ""),
        disclosure_group=str(payload.get("disclosure_group") or ""),
        article=str(payload.get("article") or ""),
        article_code=str(payload.get("article_code") or ""),
        source=str(payload.get("source") or ""),
        formula_condition=str(payload.get("formula_condition") or ""),
        required_analytics=tuple(payload.get("required_analytics") or ()),
        region_required=bool(payload.get("region_required")),
        network_required=bool(payload.get("network_required")),
        cfo_required=bool(payload.get("cfo_required")),
        organization_required=bool(payload.get("organization_required")),
        indicator_code=str(payload.get("indicator_code") or ""),
        indicator_group=str(payload.get("indicator_group") or ""),
        sales_channel=str(payload.get("sales_channel") or ""),
        predicates=predicates,
    )

