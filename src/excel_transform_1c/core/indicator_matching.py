from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .models import ArticleIndicatorRule, PreviewRecord
from .opiu_rules.opiu_rule_models import AUTO_MATCH


INDICATOR_MATCHED = "matched"
INDICATOR_AMBIGUOUS = "ambiguous"
INDICATOR_MISSING = "missing"
INDICATOR_INCOMPLETE = "incomplete"


def full_article_path(expense_type: str, expense_group: str, article_name: str) -> str:
    """Build the documented exact business path without text correction."""

    parts = tuple(value.strip() for value in (expense_type, expense_group, article_name))
    return " → ".join(parts) if all(parts) else ""


@dataclass(frozen=True)
class IndicatorMatch:
    status: str
    rule: ArticleIndicatorRule | None = None
    matched_by: str = ""
    reason: str = ""


@dataclass(frozen=True)
class IndicatorExportRow:
    organization: str
    scenario: str
    year: int
    month: int
    period: str
    sales_channel: str
    indicator: str
    amount: Decimal


class ExactArticleIndicatorMatcher:
    """Resolve one direct classifier candidate using exact, case-sensitive keys."""

    def __init__(self, rules: list[ArticleIndicatorRule]):
        # Repeated identical classifier rows still describe one candidate.
        self.rules = list(dict.fromkeys(rules))
        self.by_code: dict[str, list[ArticleIndicatorRule]] = defaultdict(list)
        self.by_path: dict[str, list[ArticleIndicatorRule]] = defaultdict(list)
        self.by_name: dict[str, list[ArticleIndicatorRule]] = defaultdict(list)
        for rule in self.rules:
            if code := rule.erp_code.strip():
                self.by_code[code].append(rule)
            if path := rule.article_path.strip():
                self.by_path[path].append(rule)
            if name := rule.article_name.strip():
                self.by_name[name].append(rule)

    def resolve(
        self,
        *,
        erp_code: str,
        expense_type: str,
        expense_group: str,
        article_name: str,
    ) -> IndicatorMatch:
        code = erp_code.strip()
        if code and (candidates := self.by_code.get(code, [])):
            return self._one(candidates, "erp_code")

        path = full_article_path(expense_type, expense_group, article_name)
        if path and (candidates := self.by_path.get(path, [])):
            return self._one(candidates, "article_path")

        name = article_name.strip()
        if name and (candidates := self.by_name.get(name, [])):
            # An exact name is authoritative only when it is unique in the
            # complete loaded classifier, irrespective of row order.
            return self._one(candidates, "article_name")

        return IndicatorMatch(
            status=INDICATOR_MISSING,
            reason="Прямое соответствие статья → показатель не найдено",
        )

    @staticmethod
    def _one(candidates: list[ArticleIndicatorRule], matched_by: str) -> IndicatorMatch:
        if len(candidates) != 1:
            return IndicatorMatch(
                status=INDICATOR_AMBIGUOUS,
                matched_by=matched_by,
                reason="Найдено несколько точных соответствий статья → показатель",
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


def apply_indicator_match(record: PreviewRecord, match: IndicatorMatch) -> None:
    record.indicator_match_status = match.status
    record.indicator_match_reason = match.reason
    if match.status == INDICATOR_MATCHED and match.rule is not None:
        record.indicator = match.rule.indicator
        record.sales_channel = match.rule.sales_channel
    else:
        record.indicator = ""
        record.sales_channel = ""


def aggregate_indicator_rows(records: list[PreviewRecord]) -> list[IndicatorExportRow]:
    """Aggregate only complete direct matches by the exact eight-column key."""

    amounts: dict[tuple[str, str, int, int, str, str, str], Decimal] = defaultdict(Decimal)
    for record in records:
        if (
            record.indicator_match_status not in {INDICATOR_MATCHED, AUTO_MATCH}
            or not record.indicator
            or not record.sales_channel
            or record.amount is None
        ):
            continue
        period = f"{record.month:02d}.{record.year}"
        key = (
            record.organization,
            record.scenario,
            record.year,
            record.month,
            period,
            record.sales_channel,
            record.indicator,
        )
        amounts[key] += record.amount

    return [
        IndicatorExportRow(*key, amount)
        for key, amount in sorted(amounts.items(), key=lambda item: item[0])
    ]
