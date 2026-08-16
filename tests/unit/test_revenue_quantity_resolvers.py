from decimal import Decimal

from excel_transform_1c.core.indicator_matching import (
    INDICATOR_AMBIGUOUS,
    INDICATOR_INCOMPLETE,
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
    ExactArticleIndicatorMatcher,
)
from excel_transform_1c.core.indicator_resolvers import (
    ExpenseResolver,
    IndicatorResolverEngine,
    QuantityResolver,
    RevenueResolver,
    detect_indicator_type,
)
from excel_transform_1c.core.models import (
    ArticleIndicatorRule,
    IndicatorType,
    PreviewRecord,
)


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
    without_formula_column = resolver.resolve(
        revenue_group="Выручка от продаж",
        article_name="Продажа товара",
        analytics="Организационные единицы | ЦФО",
    )
    explicit_different_formula = resolver.resolve(
        revenue_group="Выручка от продаж",
        article_name="Продажа товара",
        formula_condition="Источник=Другое",
        analytics="Организационные единицы | ЦФО",
    )

    assert exact.status == INDICATOR_MATCHED
    assert exact.rule and exact.rule.indicator == "Выручка"
    assert different_case.status == INDICATOR_MISSING
    assert without_formula_column.status == INDICATOR_MATCHED
    assert explicit_different_formula.status == INDICATOR_MISSING


def test_revenue_resolver_uses_full_income_hierarchy_when_rule_declares_it():
    resolver = RevenueResolver(
        [
            rule(
                indicator_type=IndicatorType.REVENUE,
                article_path="Доходы → Продажи → Продажа товара",
                revenue_group="Продажи",
                article_name="Продажа товара",
                formula_condition="Источник=Продажи",
                indicator="Выручка",
            )
        ]
    )

    exact = resolver.resolve(
        revenue_type="Доходы",
        revenue_group="Продажи",
        article_name="Продажа товара",
    )
    missing_type = resolver.resolve(
        revenue_group="Продажи",
        article_name="Продажа товара",
    )
    wrong_type = resolver.resolve(
        revenue_type="Прочие доходы",
        revenue_group="Продажи",
        article_name="Продажа товара",
    )

    assert exact.status == INDICATOR_MATCHED
    assert missing_type.status == INDICATOR_INCOMPLETE
    assert "тип доходов" in missing_type.reason
    assert wrong_type.status == INDICATOR_MISSING


def test_revenue_resolver_uses_only_analytics_declared_by_rule():
    constrained = rule(
        indicator_type=IndicatorType.REVENUE,
        revenue_group="Выручка от продаж",
        article_name="Продажа товара",
        formula_condition="Источник=Продажи",
        counterparty='ООО "Покупатель"',
        input_sales_channel="Сети Федеральные",
        sales_network="Сеть 1",
        sales_region="Приморский край",
        nomenclature="Товар А",
        indicator="Выручка сети",
    )
    resolver = RevenueResolver([constrained])
    base = {
        "revenue_group": "Выручка от продаж",
        "article_name": "Продажа товара",
        "formula_condition": "Источник=Продажи",
        "counterparty": 'ООО "Покупатель"',
        "input_sales_channel": "Сети Федеральные",
        "sales_network": "Сеть 1",
        "sales_region": "Приморский край",
        "nomenclature": "Товар А",
    }

    exact = resolver.resolve(**base, analytics="Лишнее поле входа")
    missing_region = resolver.resolve(**{**base, "sales_region": ""})
    different_region = resolver.resolve(
        **{**base, "sales_region": "Хабаровский край"}
    )
    contradicted_with_missing_field = resolver.resolve(
        **{**base, "sales_network": "Другая сеть", "sales_region": ""}
    )

    assert exact.status == INDICATOR_MATCHED
    assert exact.rule == constrained
    assert missing_region.status == INDICATOR_INCOMPLETE
    assert "регион продаж" in missing_region.reason
    assert different_region.status == INDICATOR_MISSING
    assert contradicted_with_missing_field.status == INDICATOR_MISSING


def test_revenue_resolver_never_prefers_specific_rule_over_generic_rule():
    generic = rule(
        indicator_type=IndicatorType.REVENUE,
        revenue_group="Выручка от продаж",
        article_name="Продажа товара",
        formula_condition="Источник=Продажи",
        indicator="Общая выручка",
    )
    specific = rule(
        indicator_type=IndicatorType.REVENUE,
        revenue_group="Выручка от продаж",
        article_name="Продажа товара",
        formula_condition="Источник=Продажи",
        sales_region="Приморский край",
        indicator="Выручка региона",
    )
    resolver = RevenueResolver([generic, specific])

    match = resolver.resolve(
        revenue_group="Выручка от продаж",
        article_name="Продажа товара",
        formula_condition="Источник=Продажи",
        sales_region="Приморский край",
    )

    assert match.status == INDICATOR_AMBIGUOUS
    assert match.rule is None


def test_revenue_channel_is_optional_or_copied_from_exact_input_constraint():
    other_income = rule(
        indicator_type=IndicatorType.REVENUE,
        revenue_group="Прочие доходы",
        article_name="Прочий доход",
        formula_condition="Источник=Прочее",
        indicator="Прочие доходы",
        sales_channel="",
    )
    sales = rule(
        indicator_type=IndicatorType.REVENUE,
        revenue_group="Выручка",
        article_name="Продажа",
        formula_condition="Источник=Продажи",
        indicator="Выручка",
        sales_channel="",
        input_sales_channel="Розница",
    )
    resolver = RevenueResolver([other_income, sales])

    no_channel = resolver.resolve(
        revenue_group="Прочие доходы",
        article_name="Прочий доход",
        formula_condition="Источник=Прочее",
    )
    input_channel = resolver.resolve(
        revenue_group="Выручка",
        article_name="Продажа",
        formula_condition="Источник=Продажи",
        input_sales_channel="Розница",
    )

    assert no_channel.status == INDICATOR_MATCHED
    assert no_channel.rule and no_channel.rule.sales_channel == ""
    assert input_channel.status == INDICATOR_MATCHED
    assert input_channel.rule and input_channel.rule.sales_channel == "Розница"


def test_revenue_structure_takes_priority_when_nomenclature_is_analytic():
    assert (
        detect_indicator_type(
            revenue_group="Выручка от продаж",
            formula_condition="Источник=Продажи",
            nomenclature="Товар А",
        )
        == IndicatorType.REVENUE
    )


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


def test_expense_engine_accepts_exact_rule_without_sales_channel():
    expense_rule = rule(
        erp_code="ERP-001",
        article_name="Интернет",
        indicator="Услуги связи",
        sales_channel="",
    )
    legacy_match = ExpenseResolver([expense_rule]).resolve(
        erp_code="ERP-001",
        expense_type="Административные",
        expense_group="Связь",
        article_name="Интернет",
    )
    record = PreviewRecord(
        record_id="expense-1",
        source_row=1,
        month=1,
        year=2026,
        reporting_unit="ПС",
        organization="Организация",
        scenario="ПЛАН 2026",
        department="",
        organization_type="",
        cfo="",
        expense_type="Административные",
        expense_group="Связь",
        source_article="Интернет",
        erp_code="ERP-001",
        erp_article_name="Интернет",
        tax="БЕЗ НДС",
        amount=Decimal("100"),
    )

    routed_match = IndicatorResolverEngine([expense_rule]).resolve(record)

    assert legacy_match.status == INDICATOR_INCOMPLETE
    assert routed_match.status == INDICATOR_MATCHED
    assert routed_match.rule == expense_rule
