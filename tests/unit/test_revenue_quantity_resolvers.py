from decimal import Decimal

from excel_transform_1c.core.indicator_matching import (
    INDICATOR_INCOMPLETE,
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
    ExactArticleIndicatorMatcher,
)
from excel_transform_1c.core.indicator_resolvers import (
    ExpenseResolver,
    QuantityResolver,
    RevenueResolver,
    detect_indicator_type,
)
from excel_transform_1c.core.models import ArticleIndicatorRule, IndicatorType


def rule(**overrides) -> ArticleIndicatorRule:
    values = {
        "erp_code": "",
        "article_path": "",
        "article_name": "",
        "indicator": "Показатель",
        "sales_channel": "Основной канал",
        "indicator_type": IndicatorType.EXPENSE,
        "revenue_group": "",
        "formula_condition": "",
        "analytics": "",
        "nomenclature": "",
        "unit": "",
        **overrides,
    }
    return ArticleIndicatorRule(**values)


def test_indicator_type_detection():
    assert detect_indicator_type() == IndicatorType.EXPENSE
    assert (
        detect_indicator_type(
            revenue_group="Выручка от продаж",
            formula_condition="Источник=Продажи",
            analytics="Организационные единицы | ЦФО",
        )
        == IndicatorType.REVENUE
    )
    assert (
        detect_indicator_type(nomenclature="Товар А", unit="кг")
        == IndicatorType.QUANTITY
    )
    assert detect_indicator_type(indicator_type="Доход") == IndicatorType.REVENUE


def test_revenue_resolver_exact_match():
    resolver = RevenueResolver(
        [
            rule(
                indicator_type=IndicatorType.REVENUE,
                revenue_group="Выручка от продаж",
                article_name="Продажа товара",
                formula_condition="Источник=Продажи",
                analytics="Организационные единицы | ЦФО",
                indicator="Выручка",
            )
        ]
    )

    exact = resolver.resolve(
        revenue_group="Выручка от продаж",
        article_name="Продажа товара",
        formula_condition="Источник=Продажи",
        analytics="Организационные единицы | ЦФО",
    )
    different_case = resolver.resolve(
        revenue_group="выручка от продаж",
        article_name="Продажа товара",
        formula_condition="Источник=Продажи",
        analytics="Организационные единицы | ЦФО",
    )

    assert exact.status == INDICATOR_MATCHED
    assert exact.rule and exact.rule.indicator == "Выручка"
    assert different_case.status == INDICATOR_MISSING


def test_quantity_resolver_exact_match():
    resolver = QuantityResolver(
        [
            rule(
                indicator_type=IndicatorType.QUANTITY,
                nomenclature="Товар А",
                unit="кг",
                indicator="Количество продукции",
            )
        ]
    )

    exact = resolver.resolve(
        nomenclature="Товар А",
        unit="кг",
        quantity=Decimal("5"),
    )
    no_unit = resolver.resolve(
        nomenclature="Товар А",
        unit="",
        quantity=Decimal("5"),
    )

    assert exact.status == INDICATOR_MATCHED
    assert exact.rule and exact.rule.indicator == "Количество продукции"
    assert no_unit.status == INDICATOR_INCOMPLETE


def test_expense_logic_not_changed():
    assert ExpenseResolver is ExactArticleIndicatorMatcher
    resolver = ExpenseResolver(
        [
            rule(
                erp_code="ERP-001",
                article_name="Другое",
                indicator="По коду",
            ),
            rule(
                article_path="Административные → Связь → Интернет",
                article_name="Интернет",
                indicator="По пути",
            ),
        ]
    )

    match = resolver.resolve(
        erp_code="ERP-001",
        expense_type="Административные",
        expense_group="Связь",
        article_name="Интернет",
    )

    assert match.status == INDICATOR_MATCHED
    assert match.matched_by == "erp_code"
    assert match.rule and match.rule.indicator == "По коду"
