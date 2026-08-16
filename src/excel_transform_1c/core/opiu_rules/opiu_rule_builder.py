from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from excel_transform_1c.core.models import ArticleIndicatorRule, ERPArticle

from .opiu_rule_models import (
    CatalogEntry,
    ERPIndicatorCatalogEntry,
    ERPSourceRule,
    FormulaPredicate,
    OPIUAnalyticRule,
    OPIUFormulaRule,
    OPIURule,
    OPIURuleCatalog,
    UnresolvedRule,
)


def _rule_id(parts: tuple[object, ...]) -> str:
    encoded = json.dumps(parts, ensure_ascii=False, separators=(",", ":"), default=list)
    return "opiu-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]


def _ordered_values(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def build_opiu_rule_catalog(
    formula_rules: tuple[OPIUFormulaRule, ...],
    analytic_rules: tuple[OPIUAnalyticRule, ...],
    indicator_catalog: tuple[ERPIndicatorCatalogEntry, ...],
    source_rules: tuple[ERPSourceRule, ...],
    region_catalog: tuple[CatalogEntry, ...] = (),
    network_catalog: tuple[CatalogEntry, ...] = (),
) -> OPIURuleCatalog:
    """Join the authorities by exact formula, article scope and indicator keys.

    A source value is allowed to become a disclosure group only when it was
    parsed from the proven article dimension ``С1``/``КС1``. Filters on other
    dimensions are retained as unresolved rather than being guessed as groups.
    """

    analytics_by_row = {item.source_row: item for item in analytic_rules}
    indicators: dict[tuple[str, str], list[ERPIndicatorCatalogEntry]] = defaultdict(list)
    for item in indicator_catalog:
        indicators[(item.report_line, item.column)].append(item)

    sources: dict[str, list[ERPSourceRule]] = defaultdict(list)
    for item in source_rules:
        for key in (item.code, item.formula_code.strip().strip("[]")):
            if key:
                sources[key].append(item)

    network_names = {item.name for item in network_catalog if item.name}
    rules: list[OPIURule] = []
    unresolved: list[UnresolvedRule] = []

    for formula in formula_rules:
        linked_sources = tuple(
            dict.fromkeys(
                source
                for token in formula.source_tokens
                for source in sources.get(token, ())
            )
        )
        direct_sources = tuple(source for source in linked_sources if source.register)
        if not direct_sources:
            continue

        candidates = tuple(
            dict.fromkeys(indicators.get((formula.report_indicator, formula.measure), ()))
        )
        if not candidates:
            unresolved.append(
                UnresolvedRule(
                    disclosure_group=formula.disclosure_group,
                    article=formula.article,
                    reason="Показатель не найден в ERP-каталоге",
                    required="Точная строка отчёта и колонка показателя",
                )
            )
            continue
        if len(candidates) > 1:
            unresolved.append(
                UnresolvedRule(
                    disclosure_group=formula.disclosure_group,
                    article=formula.article,
                    reason="Найдено несколько показателей в ERP-каталоге",
                    required="Однозначный код показателя",
                )
            )
            continue

        indicator = candidates[0]
        safe_sources = tuple(
            source for source in direct_sources if not source.unsupported_conditions
        )
        for source in direct_sources:
            if source.unsupported_conditions:
                unresolved.append(
                    UnresolvedRule(
                        disclosure_group=formula.disclosure_group,
                        article=formula.article,
                        reason="Условие источника не поддержано безопасным парсером",
                        required="Явный exact-отбор статьи/группы без нераспознанных условий",
                    )
                )

        group_pair_sources: dict[tuple[str, str], list[ERPSourceRule]] = defaultdict(list)
        value_pair_sources: dict[tuple[str, str], list[ERPSourceRule]] = defaultdict(list)
        for source in safe_sources:
            for group in source.disclosure_groups:
                if not group:
                    continue
                pair = (group, formula.article)
                group_pair_sources[pair].append(source)
            for article in source.article_values:
                if not article:
                    continue
                # An explicit formula leaf remains under its report hierarchy;
                # otherwise the formula disclosure group is the exact parent.
                if formula.article and article != formula.article:
                    continue
                pair = (formula.disclosure_group or article, formula.article or article)
                value_pair_sources[pair].append(source)

        if formula.article:
            pair_sources = group_pair_sources
            for pair, selected in value_pair_sources.items():
                pair_sources[pair].extend(selected)
        elif group_pair_sources:
            # A proven hierarchy root covers its exact ERP leaves. Additional
            # equality sources for the same formula are redundant and must not
            # create duplicate active rules.
            pair_sources = group_pair_sources
        else:
            pair_sources = value_pair_sources

        if not pair_sources:
            unresolved.append(
                UnresolvedRule(
                    disclosure_group=formula.disclosure_group,
                    article=formula.article,
                    reason="Не доказан exact-отбор статьи или группы раскрытия",
                    required="Отбор С1/КС1 по статье либо иерархии статьи",
                )
            )
            continue

        analytic = analytics_by_row.get(formula.source_row)
        if analytic and analytic.report_indicator != formula.report_indicator:
            unresolved.append(
                UnresolvedRule(
                    disclosure_group=formula.disclosure_group,
                    article=formula.article,
                    reason="Строка аналитик не совпадает со строкой формулы",
                    required="Точное совпадение строки формул и аналитик",
                )
            )
            analytic = None
        required_analytics = analytic.required_analytics if analytic else ()

        for (disclosure_group, article), selected_sources in pair_sources.items():
            selected = tuple(dict.fromkeys(selected_sources))
            source_names = _ordered_values(source.source for source in selected)
            source_conditions = _ordered_values(
                source.formula_condition for source in selected
            )
            predicates = tuple(
                dict.fromkeys(
                    predicate for source in selected for predicate in source.predicates
                )
            )
            formula_condition = " | ".join(
                _ordered_values((formula.formula_condition, *source_conditions))
            )
            if not disclosure_group:
                unresolved.append(
                    UnresolvedRule(
                        disclosure_group="",
                        article=article,
                        reason="Не найдена группа раскрытия",
                        required="Точная группа из отбора статьи ERP",
                    )
                )
                continue

            sales_channel = ""
            if article in network_names:
                sales_channel = article
            elif disclosure_group in network_names:
                sales_channel = disclosure_group

            parts = (
                formula.source_row,
                formula.report_line,
                indicator.indicator_code,
                disclosure_group,
                article,
                source_names,
                formula_condition,
                required_analytics,
                tuple((item.field, item.expected) for item in predicates),
            )
            rules.append(
                OPIURule(
                    rule_id=_rule_id(parts),
                    report_line=formula.report_line,
                    report_indicator=indicator.name,
                    disclosure_group=disclosure_group,
                    article=article,
                    article_code="",
                    source="; ".join(source_names),
                    formula_condition=formula_condition,
                    required_analytics=required_analytics,
                    region_required=bool(analytic and analytic.region_required),
                    network_required=bool(analytic and analytic.network_required),
                    cfo_required=bool(analytic and analytic.cfo_required),
                    organization_required=bool(
                        analytic and analytic.organization_required
                    ),
                    indicator_code=indicator.indicator_code,
                    indicator_group=indicator.indicator_group,
                    sales_channel=sales_channel,
                    predicates=predicates,
                )
            )
            if not article:
                unresolved.append(
                    UnresolvedRule(
                        disclosure_group=disclosure_group,
                        article="",
                        reason="Источник задаёт группу, но не перечисляет статьи внутри неё",
                        required="Точный каталог статей внутри группы раскрытия",
                    )
                )

    return OPIURuleCatalog(
        formula_rules=formula_rules,
        analytic_rules=analytic_rules,
        indicator_catalog=indicator_catalog,
        source_rules=source_rules,
        region_catalog=region_catalog,
        network_catalog=network_catalog,
        rules=tuple(dict.fromkeys(rules)),
        unresolved=tuple(dict.fromkeys(unresolved)),
    )

def legacy_rules_to_opiu(rules: list[ArticleIndicatorRule]) -> tuple[OPIURule, ...]:
    """Keep the old upload endpoint usable only for full group/article paths."""

    converted: list[OPIURule] = []
    for rule in rules:
        path = tuple(part.strip() for part in rule.article_path.split("→"))
        if len(path) < 2 or not path[0] or not path[-1]:
            continue
        parts = (path[0], path[-1], rule.erp_code, rule.indicator, rule.sales_channel)
        converted.append(
            OPIURule(
                rule_id=_rule_id(parts),
                report_line=path[0],
                report_indicator=rule.indicator,
                disclosure_group=path[0],
                article=path[-1],
                article_code=rule.erp_code,
                source="Загруженный классификатор",
                formula_condition="",
                required_analytics=(),
                region_required=False,
                network_required=False,
                cfo_required=False,
                indicator_code="",
                sales_channel=rule.sales_channel,
            )
        )
    return tuple(dict.fromkeys(converted))


def _semantic_rule_key(rule: OPIURule) -> tuple[object, ...]:
    return (
        rule.report_line,
        rule.report_indicator,
        rule.disclosure_group,
        rule.article,
        rule.article_code,
        rule.source,
        rule.formula_condition,
        rule.required_analytics,
        rule.region_required,
        rule.network_required,
        rule.cfo_required,
        rule.organization_required,
        rule.indicator_code,
        rule.indicator_group,
        rule.sales_channel,
        rule.predicates,
    )


def expand_group_rules(
    rules: tuple[OPIURule, ...],
    articles: list[ERPArticle],
) -> tuple[OPIURule, ...]:
    """Expand a proven group at any exact ERP hierarchy level.

    The same display text may occur at more than one level or path. Article code
    remains part of the resulting identity, so a missing code is ambiguous
    rather than guessed.
    """

    expanded: list[OPIURule] = [rule for rule in rules if rule.article]
    for rule in rules:
        if rule.article:
            continue
        for article in articles:
            hierarchy = (
                article.expense_type,
                article.expense_group,
                article.source_article,
            )
            if rule.disclosure_group not in hierarchy:
                continue
            parts = (rule.rule_id, article.code, article.source_article)
            expanded.append(
                OPIURule(
                    **{
                        **rule.__dict__,
                        "rule_id": _rule_id(parts),
                        "article": article.source_article,
                        "article_code": article.code,
                    }
                )
            )

    deduplicated: dict[tuple[object, ...], OPIURule] = {}
    for rule in expanded:
        deduplicated.setdefault(_semantic_rule_key(rule), rule)
    return tuple(deduplicated.values())
