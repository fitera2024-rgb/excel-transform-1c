from __future__ import annotations

from collections import defaultdict

from .opiu_rule_models import (
    AMBIGUOUS,
    AUTO_MATCH,
    NOT_FOUND,
    OPIUMatchResult,
    OPIUResolutionContext,
    OPIURule,
)


class OPIUIndicatorResolver:
    """Resolve by exact disclosure group, then exact article and predicates."""

    def __init__(self, rules: tuple[OPIURule, ...] | list[OPIURule]):
        self.rules = tuple(dict.fromkeys(rules))
        self.by_group: dict[str, list[OPIURule]] = defaultdict(list)
        for rule in self.rules:
            group = rule.disclosure_group.strip()
            if group:
                self.by_group[group].append(rule)

    def resolve(
        self,
        *,
        disclosure_group: str,
        article: str,
        article_code: str = "",
        organization: str = "",
        cfo: str = "",
        region: str = "",
        network: str = "",
        nomenclature: str = "",
        analytics: dict[str, str] | None = None,
    ) -> OPIUMatchResult:
        group = disclosure_group.strip()
        if not group or group not in self.by_group:
            return OPIUMatchResult(
                status=NOT_FOUND,
                reason="Не найдена группа раскрытия",
            )
        article_name = article.strip()
        if not article_name:
            return OPIUMatchResult(
                status=NOT_FOUND,
                reason="Не найдена статья внутри группы раскрытия",
            )

        group_rules = self.by_group[group]
        exact = [rule for rule in group_rules if rule.article == article_name]
        if article_code.strip():
            exact_code = [
                rule
                for rule in exact
                if not rule.article_code or rule.article_code == article_code.strip()
            ]
            exact = exact_code
        candidates = exact
        if not candidates:
            return OPIUMatchResult(
                status=NOT_FOUND,
                reason="Статья не найдена внутри группы раскрытия",
            )

        context = OPIUResolutionContext(
            disclosure_group=group,
            article=article_name,
            article_code=article_code.strip(),
            organization=organization.strip(),
            cfo=cfo.strip(),
            region=region.strip(),
            network=network.strip(),
            nomenclature=nomenclature.strip(),
            analytics=dict(analytics or {}),
        )
        matched = tuple(
            dict.fromkeys(rule for rule in candidates if self._matches(rule, context))
        )
        if not matched:
            return OPIUMatchResult(
                status=NOT_FOUND,
                reason=self._missing_reason(candidates, context),
            )
        if len(matched) > 1:
            return OPIUMatchResult(
                status=AMBIGUOUS,
                reason="Найдено несколько показателей",
            )
        return OPIUMatchResult(status=AUTO_MATCH, rule=matched[0])

    @staticmethod
    def _matches(rule: OPIURule, context: OPIUResolutionContext) -> bool:
        if rule.organization_required and not context.organization:
            return False
        if rule.cfo_required and not context.cfo:
            return False
        if rule.region_required and not context.region:
            return False
        if rule.network_required and not context.network:
            return False
        values = {
            "organization": context.organization,
            "cfo": context.cfo,
            "region": context.region,
            "network": context.network,
            "nomenclature": context.nomenclature,
            "article_code": context.article_code,
            **context.analytics,
        }
        return all(values.get(item.field, "") == item.expected for item in rule.predicates)

    @staticmethod
    def _missing_reason(
        candidates: list[OPIURule], context: OPIUResolutionContext
    ) -> str:
        requirements = (
            ("organization_required", context.organization, "Организация"),
            ("cfo_required", context.cfo, "ЦФО"),
            ("region_required", context.region, "Регион"),
            ("network_required", context.network, "Сеть"),
        )
        missing = [
            label
            for attribute, value, label in requirements
            if not value and any(getattr(rule, attribute) for rule in candidates)
        ]
        if missing:
            return "Не заполнена обязательная аналитика: " + ", ".join(missing)
        return "Условия формулы не выполнены"
