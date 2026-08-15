from excel_transform_1c.core.indicator_matching import (
    INDICATOR_MATCHED,
    ExactArticleIndicatorMatcher,
    full_article_path,
)
from excel_transform_1c.core.models import ArticleIndicatorRule


def rule(path: str, indicator: str, *, name: str = "Комиссия") -> ArticleIndicatorRule:
    return ArticleIndicatorRule("", path, name, indicator, "Розница")


def test_exact_path_preserves_empty_group():
    assert full_article_path("Коммерческие расходы", "", "Комиссия") == (
        "Коммерческие расходы →  → Комиссия"
    )


def test_type_empty_group_article_matches_exact_path():
    matcher = ExactArticleIndicatorMatcher(
        [rule("Коммерческие расходы →  → Комиссия", "Комиссии")]
    )
    match = matcher.resolve(
        erp_code="",
        expense_type="Коммерческие расходы",
        expense_group="",
        article_name="Комиссия",
    )
    assert match.status == INDICATOR_MATCHED
    assert match.matched_by == "article_path"
    assert match.rule and match.rule.indicator == "Комиссии"


def test_same_article_in_different_types_with_empty_group_is_not_ambiguous_by_path():
    matcher = ExactArticleIndicatorMatcher(
        [
            rule("Коммерческие расходы →  → Комиссия", "Комиссии"),
            rule("Административные расходы →  → Комиссия", "Банковские комиссии"),
        ]
    )
    match = matcher.resolve(
        erp_code="",
        expense_type="Административные расходы",
        expense_group="",
        article_name="Комиссия",
    )
    assert match.status == INDICATOR_MATCHED
    assert match.rule and match.rule.indicator == "Банковские комиссии"


def test_exact_empty_level_path_prevents_name_only_fallback():
    matcher = ExactArticleIndicatorMatcher(
        [
            rule("Коммерческие расходы →  → Комиссия", "Комиссии"),
            rule("Административные расходы →  → Комиссия", "Банковские комиссии"),
        ]
    )
    match = matcher.resolve(
        erp_code="",
        expense_type="Коммерческие расходы",
        expense_group="",
        article_name="Комиссия",
    )
    assert match.status == INDICATOR_MATCHED
    assert match.matched_by == "article_path"
