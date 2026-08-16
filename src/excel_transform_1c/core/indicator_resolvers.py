from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from .indicator_matching import (
    INDICATOR_AMBIGUOUS,
    INDICATOR_INCOMPLETE,
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
    ExactArticleIndicatorMatcher,
    IndicatorMatch,
)
from .models import ArticleIndicatorRule, IndicatorType, PreviewRecord


# The expense resolver is deliberately the existing exact matcher.  Keeping an
# alias here lets the routing engine name all three business paths without
# changing the proven expense implementation.
ExpenseResolver = ExactArticleIndicatorMatcher


_EXPLICIT_TYPES = {
    "EXPENSE": IndicatorType.EXPENSE,
    "Расход": IndicatorType.EXPENSE,
    "REVENUE": IndicatorType.REVENUE,
    "Доход": IndicatorType.REVENUE,
    "QUANTITY": IndicatorType.QUANTITY,
    "Количество": IndicatorType.QUANTITY,
}


def detect_indicator_type(
    *,
    indicator_type: Any = "",
    revenue_group: Any = "",
    formula_condition: Any = "",
    analytics: Any = "",
    nomenclature: Any = "",
    unit: Any = "",
) -> IndicatorType:
    """Classify by explicit value or structural fields, never by display name."""

    explicit = str(indicator_type or "").strip()
    if explicit:
        try:
            return _EXPLICIT_TYPES[explicit]
        except KeyError as exc:
            raise ValueError(f"Неизвестный тип показателя: {explicit}") from exc

    has_revenue_structure = any(
        str(value or "").strip()
        for value in (revenue_group, formula_condition, analytics)
    )
    has_quantity_structure = any(
        str(value or "").strip() for value in (nomenclature, unit)
    )
    if has_revenue_structure and has_quantity_structure:
        raise ValueError(
            "Тип показателя неоднозначен: одновременно заполнены поля дохода и количества"
        )
    if has_revenue_structure:
        return IndicatorType.REVENUE
    if has_quantity_structure:
        return IndicatorType.QUANTITY
    # Legacy classifier rows are the accepted expense contract.
    return IndicatorType.EXPENSE


def _rule_type(rule: ArticleIndicatorRule) -> IndicatorType:
    return detect_indicator_type(
        indicator_type=rule.indicator_type,
        revenue_group=rule.revenue_group,
        formula_condition=rule.formula_condition,
        analytics=rule.analytics,
        nomenclature=rule.nomenclature,
        unit=rule.unit,
    )


def _resolved_candidate(
    candidates: list[ArticleIndicatorRule],
    *,
    matched_by: str,
    ambiguous_reason: str,
) -> IndicatorMatch:
    if len(candidates) != 1:
        return IndicatorMatch(
            status=INDICATOR_AMBIGUOUS,
            matched_by=matched_by,
            reason=ambiguous_reason,
        )
    rule = candidates[0]
    if not rule.indicator.strip() or not rule.sales_channel.strip():
        return IndicatorMatch(
            status=INDICATOR_INCOMPLETE,
            rule=rule,
            matched_by=matched_by,
            reason="В точном соответствии не заполнен показатель или канал сбыта",
        )
    return IndicatorMatch(
        status=INDICATOR_MATCHED,
        rule=rule,
        matched_by=matched_by,
    )


class RevenueResolver:
    """Exact chain: revenue group → article → formula → analytics → indicator."""

    def __init__(self, rules: list[ArticleIndicatorRule]):
        self.by_key: dict[tuple[str, str, str, str], list[ArticleIndicatorRule]] = (
            defaultdict(list)
        )
        for rule in dict.fromkeys(rules):
            if _rule_type(rule) != IndicatorType.REVENUE:
                continue
            key = (
                rule.revenue_group.strip(),
                rule.article_name.strip(),
                rule.formula_condition.strip(),
                rule.analytics.strip(),
            )
            self.by_key[key].append(rule)

    def resolve(
        self,
        *,
        revenue_group: str,
        article_name: str,
        formula_condition: str,
        analytics: str,
    ) -> IndicatorMatch:
        key = tuple(
            value.strip()
            for value in (
                revenue_group,
                article_name,
                formula_condition,
                analytics,
            )
        )
        if not all(key):
            return IndicatorMatch(
                status=INDICATOR_INCOMPLETE,
                reason=(
                    "Для дохода не заполнена точная цепочка: группа, статья, "
                    "условия формулы и аналитики"
                ),
            )
        candidates = self.by_key.get(key, [])
        if not candidates:
            return IndicatorMatch(
                status=INDICATOR_MISSING,
                reason="Точное соответствие дохода показателю не найдено",
            )
        return _resolved_candidate(
            candidates,
            matched_by="revenue_chain",
            ambiguous_reason=(
                "Найдено несколько точных соответствий по группе дохода, статье, "
                "условиям формулы и аналитикам"
            ),
        )


class QuantityResolver:
    """Exact chain: nomenclature → unit → quantity present → indicator."""

    def __init__(self, rules: list[ArticleIndicatorRule]):
        self.by_key: dict[tuple[str, str], list[ArticleIndicatorRule]] = defaultdict(list)
        for rule in dict.fromkeys(rules):
            if _rule_type(rule) != IndicatorType.QUANTITY:
                continue
            self.by_key[(rule.nomenclature.strip(), rule.unit.strip())].append(rule)

    def resolve(
        self,
        *,
        nomenclature: str,
        unit: str,
        quantity: Decimal | None,
    ) -> IndicatorMatch:
        if quantity is None:
            return IndicatorMatch(
                status=INDICATOR_INCOMPLETE,
                reason="В исходных данных не заполнено количество",
            )
        key = (nomenclature.strip(), unit.strip())
        if not key[0]:
            return IndicatorMatch(
                status=INDICATOR_INCOMPLETE,
                reason="В исходных данных не заполнена номенклатура",
            )
        if not key[1]:
            return IndicatorMatch(
                status=INDICATOR_INCOMPLETE,
                reason="В исходных данных не заполнена единица измерения",
            )
        candidates = self.by_key.get(key, [])
        if not candidates:
            return IndicatorMatch(
                status=INDICATOR_MISSING,
                reason="Точная связь количества с показателем не найдена",
            )
        return _resolved_candidate(
            candidates,
            matched_by="quantity_chain",
            ambiguous_reason=(
                "Найдено несколько точных показателей для номенклатуры и единицы измерения"
            ),
        )


class IndicatorResolverEngine:
    """Route a preview row to one deterministic business resolver."""

    def __init__(self, rules: list[ArticleIndicatorRule]):
        expense_rules = [
            rule for rule in rules if _rule_type(rule) == IndicatorType.EXPENSE
        ]
        self.expense = ExpenseResolver(expense_rules)
        self.revenue = RevenueResolver(rules)
        self.quantity = QuantityResolver(rules)

    def resolve(self, record: PreviewRecord) -> IndicatorMatch:
        if record.indicator_type == IndicatorType.REVENUE:
            return self.revenue.resolve(
                revenue_group=record.revenue_group,
                article_name=record.source_article,
                formula_condition=record.formula_condition,
                analytics=record.analytics,
            )
        if record.indicator_type == IndicatorType.QUANTITY:
            return self.quantity.resolve(
                nomenclature=record.nomenclature,
                unit=record.unit,
                quantity=record.amount,
            )
        return self.expense.resolve(
            erp_code=record.erp_code,
            expense_type=record.expense_type,
            expense_group=record.expense_group,
            article_name=record.source_article,
        )
