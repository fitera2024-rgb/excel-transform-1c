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
    """Join the four authorities without name-only or row-order guessing."""

    analytics_by_row = {item.source_row: item for item in analytic_rules}
    indicators: dict[tuple[str, str], list[ERPIndicatorCatalogEntry]] = defaultdict(list)
    for item in indicator_catalog:
        indicators[(item.report_line, item.column)].append(item)

    sources: dict[str, list[ERPSourceRule]] = defaultdict(list)
    for item in source_rules:
        for key in (item.code, item.formula_code.strip().strip("[]")):
            if key:
                sources[key].append(item)

    network_names = {item.name for item in network_catalog}
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
        source_groups = _ordered_values(
            group for source in direct_sources for group in source.disclosure_groups
        )
        disclosure_groups = source_groups or (formula.disclosure_group,)
        analytic = analytics_by_row.get(formula.source_row)
        required_analytics = analytic.required_analytics if analytic else ()
        source_names = _ordered_values(source.source for source in direct_sources)
        source_conditions = _ordered_values(
            source.formula_condition for source in direct_sources
        )
        predicates = tuple(
            dict.fromkeys(
                predicate for source in direct_sources for predicate in source.predicates
            )
        )
        formula_condition = " | ".join(
            _ordered_values((formula.formula_condition, *source_conditions))
        )

        for disclosure_group in disclosure_groups:
            if not disclosure_group:
                unresolved.append(
                    UnresolvedRule(
                        disclosure_group="",
                        article=formula.article,
                        reason="Не найдена группа раскрытия",
                        required="Точная группа из условия источника ERP",
                    )
                )
                continue
            sales_channel = ""
            if formula.article in network_names:
                sales_channel = formula.article
            elif disclosure_group in network_names:
                sales_channel = disclosure_group
            parts = (
                formula.source_row,
                formula.report_line,
                indicator.indicator_code,
                disclosure_group,
                formula.article,
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
                    article=formula.article,
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
            if not formula.article:
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


def expand_group_rules(
    rules: tuple[OPIURule, ...],
    articles: list[ERPArticle],
) -> tuple[OPIURule, ...]:
    """Expand only exact expense-type membership; retain explicit group scopes."""

    expanded = [rule for rule in rules if rule.article]
    for rule in rules:
        if rule.article:
            continue
        for article in articles:
            if article.expense_type != rule.disclosure_group:
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
    return tuple(dict.fromkeys(expanded))
