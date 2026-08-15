from decimal import Decimal

from excel_transform_1c.core.indicator_matching import (
    INDICATOR_AMBIGUOUS,
    INDICATOR_INCOMPLETE,
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
    ExactArticleIndicatorMatcher,
    aggregate_indicator_rows,
)
from excel_transform_1c.core.models import ArticleIndicatorRule, PreviewRecord


def rule(
    *,
    erp_code: str = "",
    article_path: str = "",
    article_name: str = "",
    indicator: str = "Показатель",
    sales_channel: str = "Канал",
) -> ArticleIndicatorRule:
    return ArticleIndicatorRule(
        erp_code=erp_code,
        article_path=article_path,
        article_name=article_name,
        indicator=indicator,
        sales_channel=sales_channel,
    )


def resolve(matcher: ExactArticleIndicatorMatcher, **overrides):
    values = {
        "erp_code": "ERP-001",
        "expense_type": "Административные",
        "expense_group": "Связь",
        "article_name": "Интернет",
        **overrides,
    }
    return matcher.resolve(**values)


def test_exact_erp_code_has_first_priority():
    matcher = ExactArticleIndicatorMatcher(
        [
            rule(erp_code="ERP-001", article_name="Другое", indicator="По коду"),
            rule(article_path="Административные → Связь → Интернет", indicator="По пути"),
        ]
    )

    match = resolve(matcher)

    assert match.status == INDICATOR_MATCHED
    assert match.matched_by == "erp_code"
    assert match.rule and match.rule.indicator == "По коду"


def test_exact_full_path_is_used_when_code_has_no_candidate():
    matcher = ExactArticleIndicatorMatcher(
        [rule(article_path="Административные → Связь → Интернет", indicator="По пути")]
    )

    match = resolve(matcher, erp_code="ERP-UNKNOWN")

    assert match.status == INDICATOR_MATCHED
    assert match.matched_by == "article_path"


def test_exact_name_is_allowed_only_when_unique_in_classifier():
    matcher = ExactArticleIndicatorMatcher([rule(article_name="Интернет")])

    match = resolve(matcher, erp_code="", expense_type="", expense_group="")

    assert match.status == INDICATOR_MATCHED
    assert match.matched_by == "article_name"


def test_two_exact_name_candidates_are_never_selected_by_order():
    rules = [
        rule(erp_code="ERP-001", article_name="Интернет", indicator="Первый"),
        rule(erp_code="ERP-002", article_name="Интернет", indicator="Второй"),
    ]

    for ordered in (rules, list(reversed(rules))):
        match = resolve(
            ExactArticleIndicatorMatcher(ordered),
            erp_code="",
            expense_type="",
            expense_group="",
        )
        assert match.status == INDICATOR_AMBIGUOUS
        assert match.rule is None


def test_missing_candidate_stays_missing():
    match = resolve(ExactArticleIndicatorMatcher([]))

    assert match.status == INDICATOR_MISSING
    assert match.rule is None


def test_case_difference_is_not_corrected():
    matcher = ExactArticleIndicatorMatcher([rule(article_name="Интернет")])

    match = resolve(
        matcher,
        erp_code="",
        expense_type="",
        expense_group="",
        article_name="интернет",
    )

    assert match.status == INDICATOR_MISSING


def test_typo_and_contains_are_not_corrected():
    matcher = ExactArticleIndicatorMatcher([rule(article_name="Интернет")])

    typo = resolve(
        matcher,
        erp_code="",
        expense_type="",
        expense_group="",
        article_name="Интерент",
    )
    contains = resolve(
        matcher,
        erp_code="",
        expense_type="",
        expense_group="",
        article_name="Интернет резервный",
    )

    assert typo.status == INDICATOR_MISSING
    assert contains.status == INDICATOR_MISSING


def test_incomplete_direct_rule_requires_attention():
    matcher = ExactArticleIndicatorMatcher(
        [rule(erp_code="ERP-001", sales_channel="")]
    )

    match = resolve(matcher)

    assert match.status == INDICATOR_INCOMPLETE
    assert match.rule is not None


def record(
    record_id: str,
    *,
    amount: Decimal | None,
    month: int = 1,
    channel: str = "Канал",
    indicator: str = "Показатель",
) -> PreviewRecord:
    return PreviewRecord(
        record_id=record_id,
        source_row=int(record_id),
        month=month,
        year=2026,
        reporting_unit="ПС",
        organization="Организация",
        scenario="ПЛАН 2026",
        department="",
        organization_type="",
        cfo="",
        expense_type="",
        expense_group="",
        source_article="",
        erp_code="",
        erp_article_name="",
        tax="",
        amount=amount,
        indicator=indicator,
        sales_channel=channel,
        indicator_match_status=INDICATOR_MATCHED,
    )


def test_indicator_rows_aggregate_equal_keys_and_keep_zero_and_negative():
    records = [
        record("1", amount=Decimal("10")),
        record("2", amount=Decimal("-3")),
        record("3", amount=Decimal("0"), channel="Нулевой"),
        record("4", amount=Decimal("-5"), channel="Отрицательный"),
        record("5", amount=None, channel="Ошибка месяца"),
    ]

    rows = aggregate_indicator_rows(records)
    amounts = {row.sales_channel: row.amount for row in rows}

    assert amounts == {
        "Канал": Decimal("7"),
        "Нулевой": Decimal("0"),
        "Отрицательный": Decimal("-5"),
    }
    assert "Ошибка месяца" not in amounts
