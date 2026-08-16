from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from decimal import Decimal
from typing import Any

from .indicator_matching import (
    INDICATOR_AMBIGUOUS,
    INDICATOR_INCOMPLETE,
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
    ExactArticleIndicatorMatcher,
    IndicatorMatch,
    full_article_path,
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
    counterparty: Any = "",
    input_sales_channel: Any = "",
    sales_network: Any = "",
    sales_region: Any = "",
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
        for value in (
            revenue_group,
            formula_condition,
            analytics,
            counterparty,
            input_sales_channel,
            sales_network,
            sales_region,
        )
    )
    has_quantity_structure = any(
        str(value or "").strip() for value in (nomenclature, unit)
    )
    # Nomenclature is also a valid optional revenue analytic. Revenue-specific
    # structure therefore takes precedence; quantity is inferred only when no
    # revenue field is present.
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
        counterparty=rule.counterparty,
        input_sales_channel=rule.input_sales_channel,
        sales_network=rule.sales_network,
        sales_region=rule.sales_region,
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
    indicator_missing = not rule.indicator.strip()
    if indicator_missing:
        return IndicatorMatch(
            status=INDICATOR_INCOMPLETE,
            rule=rule,
            matched_by=matched_by,
            reason="В точной связи не заполнен показатель",
        )
    return IndicatorMatch(
        status=INDICATOR_MATCHED,
        rule=rule,
        matched_by=matched_by,
    )


def _expense_channel_optional(match: IndicatorMatch) -> IndicatorMatch:
    """Accept an exact expense rule when its only absent field is sales channel.

    The legacy exact matcher deliberately keeps its original completeness
    contract.  The type-aware routing layer owns the newer rule that a sales
    channel is a revenue analytic and is not required for an expense result.
    """

    rule = match.rule
    if (
        match.status == INDICATOR_INCOMPLETE
        and rule is not None
        and _rule_type(rule) == IndicatorType.EXPENSE
        and rule.indicator.strip()
        and not rule.sales_channel.strip()
    ):
        return IndicatorMatch(
            status=INDICATOR_MATCHED,
            rule=rule,
            matched_by=match.matched_by,
        )
    return match


class SelectionExpenseResolver:
    """Resolve packaged expense rules proven by exact MXL hierarchy filters.

    These rules intentionally require the complete disclosure-group path and
    never fall back to an ERP code or a globally unique article title. The
    legacy ``ExpenseResolver`` remains unchanged for uploaded direct rules.
    """

    def __init__(self, rules: list[ArticleIndicatorRule]):
        self.by_path: dict[str, list[ArticleIndicatorRule]] = defaultdict(list)
        for rule in dict.fromkeys(rules):
            if _rule_type(rule) != IndicatorType.EXPENSE:
                continue
            if not rule.formula_condition.strip():
                continue
            if path := rule.article_path.strip():
                self.by_path[path].append(rule)

    def resolve(
        self,
        *,
        expense_type: str,
        expense_group: str,
        article_name: str,
    ) -> IndicatorMatch:
        if not expense_group.strip():
            return IndicatorMatch(
                status=INDICATOR_MISSING,
                reason="Для расхода не заполнена группа раскрытия",
            )
        path = full_article_path(expense_type, expense_group, article_name)
        candidates = self.by_path.get(path, [])
        if not candidates:
            return IndicatorMatch(
                status=INDICATOR_MISSING,
                reason="Точная связь группы, статьи и условий формулы не найдена",
            )
        return _resolved_candidate(
            candidates,
            matched_by="expense_group_formula",
            ambiguous_reason=(
                "Найдено несколько точных показателей по группе, статье "
                "и условиям формулы"
            ),
        )


class RevenueResolver:
    """Resolve an exact revenue base plus only rule-declared analytics."""

    CONCRETE_FIELDS = (
        ("counterparty", "контрагент"),
        ("input_sales_channel", "ИНТ канал сбыта"),
        ("sales_network", "сеть"),
        ("sales_region", "регион продаж"),
        ("nomenclature", "номенклатура"),
    )
    REQUIRED_ANALYTICS = {
        "Контрагент": ("counterparty", "контрагент"),
        "ИНТ канал сбыта": ("input_sales_channel", "ИНТ канал сбыта"),
        "Канал сбыта": ("input_sales_channel", "ИНТ канал сбыта"),
        "Сеть": ("sales_network", "сеть"),
        "Регион продаж": ("sales_region", "регион продаж"),
        "Номенклатура": ("nomenclature", "номенклатура"),
        "ИНТ номенклатура": ("nomenclature", "номенклатура"),
    }
    CONTEXT_ANALYTICS = {
        "Организационные единицы",
        "ЦФО",
        "ЦФО (казначейство)",
    }

    def __init__(self, rules: list[ArticleIndicatorRule]):
        self.by_article: dict[str, list[ArticleIndicatorRule]] = defaultdict(list)
        for rule in dict.fromkeys(rules):
            if _rule_type(rule) != IndicatorType.REVENUE:
                continue
            if article := rule.article_name.strip():
                self.by_article[article].append(rule)

    def resolve(
        self,
        *,
        revenue_group: str,
        article_name: str,
        formula_condition: str = "",
        analytics: str = "",
        counterparty: str = "",
        input_sales_channel: str = "",
        sales_network: str = "",
        sales_region: str = "",
        nomenclature: str = "",
        revenue_type: str = "",
        hierarchy_group: str = "",
    ) -> IndicatorMatch:
        article = article_name.strip()
        group = revenue_group.strip() or hierarchy_group.strip()
        if not article or not group:
            return IndicatorMatch(
                status=INDICATOR_INCOMPLETE,
                reason=(
                    "Для дохода не заполнена точная основа: группа и статья"
                ),
            )
        base_candidates = self.by_article.get(article, [])
        if not base_candidates:
            return IndicatorMatch(
                status=INDICATOR_MISSING,
                reason="Точное соответствие дохода показателю не найдено",
            )
        revenue_type = revenue_type.strip()
        actual_path = full_article_path(revenue_type, group, article)
        input_formula = formula_condition.strip()
        actual = {
            "analytics": analytics.strip(),
            "counterparty": counterparty.strip(),
            "input_sales_channel": input_sales_channel.strip(),
            "sales_network": sales_network.strip(),
            "sales_region": sales_region.strip(),
            "nomenclature": nomenclature.strip(),
        }
        candidates: list[ArticleIndicatorRule] = []
        missing_labels: set[str] = set()
        for rule in base_candidates:
            missing_for_rule: list[str] = []
            mismatched = False
            expected_group = rule.revenue_group.strip()
            if expected_group and group != expected_group:
                mismatched = True
            expected_path = rule.article_path.strip()
            if expected_path:
                if not revenue_type:
                    missing_for_rule.append("тип доходов")
                elif actual_path != expected_path:
                    mismatched = True
            expected_formula = rule.formula_condition.strip()
            if expected_formula and input_formula and input_formula != expected_formula:
                mismatched = True
            for field, label in self.CONCRETE_FIELDS:
                expected = getattr(rule, field).strip()
                if not expected:
                    continue
                value = actual[field]
                if not value:
                    missing_for_rule.append(label)
                elif value != expected:
                    mismatched = True
            expected_analytics = rule.analytics.strip()
            if expected_analytics:
                tokens = tuple(expected_analytics.split(" | "))
                known_tokens = self.CONTEXT_ANALYTICS | set(
                    self.REQUIRED_ANALYTICS
                )
                if all(token in known_tokens for token in tokens):
                    for token in tokens:
                        required = self.REQUIRED_ANALYTICS.get(token)
                        if required is None:
                            continue
                        field, label = required
                        if not actual[field]:
                            missing_for_rule.append(label)
                else:
                    # Backward-compatible uploaded rules may still provide one
                    # exact opaque analytics key. It is compared literally and
                    # is never tokenized, normalized or partially matched.
                    if not actual["analytics"]:
                        missing_for_rule.append("аналитики")
                    elif actual["analytics"] != expected_analytics:
                        mismatched = True
            if mismatched:
                continue
            if missing_for_rule:
                missing_labels.update(missing_for_rule)
                continue
            candidates.append(rule)

        if not candidates and missing_labels:
            return IndicatorMatch(
                status=INDICATOR_INCOMPLETE,
                reason=(
                    "Для дохода не заполнены поля точного правила: "
                    + ", ".join(sorted(missing_labels))
                ),
            )
        if not candidates:
            return IndicatorMatch(
                status=INDICATOR_MISSING,
                reason="Точное соответствие дохода показателю не найдено",
            )
        if (
            len(candidates) == 1
            and not candidates[0].sales_channel.strip()
            and candidates[0].input_sales_channel.strip()
        ):
            candidates = [
                replace(
                    candidates[0],
                    sales_channel=actual["input_sales_channel"],
                )
            ]
        return _resolved_candidate(
            candidates,
            matched_by="revenue_chain",
            ambiguous_reason=(
                "Найдено несколько точных соответствий по иерархии дохода, "
                "статье и объявленным условиям аналитики"
            ),
        )


class QuantityResolver:
    """Exact chain: nomenclature → unit → quantity present → indicator."""

    def __init__(self, rules: list[ArticleIndicatorRule]):
        self.by_key: dict[tuple[str, str], list[ArticleIndicatorRule]] = defaultdict(list)
        for rule in dict.fromkeys(rules):
            if _rule_type(rule) != IndicatorType.QUANTITY:
                continue
            nomenclature = rule.nomenclature.strip()
            unit = rule.unit.strip()
            if nomenclature and unit:
                self.by_key[(nomenclature, unit)].append(rule)

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
        selection_rules = [
            rule for rule in expense_rules if rule.formula_condition.strip()
        ]
        direct_rules = [
            rule for rule in expense_rules if not rule.formula_condition.strip()
        ]
        self.expense = ExpenseResolver(direct_rules)
        self.selection_expense = SelectionExpenseResolver(selection_rules)
        self.revenue = RevenueResolver(rules)
        self.quantity = QuantityResolver(rules)

    def resolve(self, record: PreviewRecord) -> IndicatorMatch:
        if record.indicator_type == IndicatorType.REVENUE:
            return self.revenue.resolve(
                revenue_group=record.revenue_group,
                article_name=record.source_article,
                formula_condition=record.formula_condition,
                analytics=record.analytics,
                counterparty=record.counterparty,
                input_sales_channel=record.input_sales_channel,
                sales_network=record.sales_network,
                sales_region=record.sales_region,
                nomenclature=record.nomenclature,
                revenue_type=record.expense_type,
                hierarchy_group=record.expense_group,
            )
        if record.indicator_type == IndicatorType.QUANTITY:
            return self.quantity.resolve(
                nomenclature=record.nomenclature,
                unit=record.unit,
                quantity=record.amount,
            )
        direct = self.expense.resolve(
            erp_code=record.erp_code,
            expense_type=record.expense_type,
            expense_group=record.expense_group,
            article_name=record.source_article,
        )
        if direct.status != INDICATOR_MISSING:
            return _expense_channel_optional(direct)
        return self.selection_expense.resolve(
            expense_type=record.expense_type,
            expense_group=record.expense_group,
            article_name=record.source_article,
        )
