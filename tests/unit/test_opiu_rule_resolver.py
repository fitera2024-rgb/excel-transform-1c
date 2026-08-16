from excel_transform_1c.core.opiu_rules.opiu_formula_parser import (
    _parse_source_condition,
    parse_formula_rows,
)
from excel_transform_1c.core.opiu_rules.opiu_indicator_resolver import (
    OPIUIndicatorResolver,
)
from excel_transform_1c.core.opiu_rules.opiu_rule_models import (
    AMBIGUOUS,
    AUTO_MATCH,
    NOT_FOUND,
    FormulaInputRow,
    FormulaPredicate,
    OPIURule,
)


def rule(
    rule_id: str,
    *,
    group: str = "Административные",
    article: str = "Интернет",
    indicator: str = "Административные",
    predicates: tuple[FormulaPredicate, ...] = (),
    region_required: bool = False,
    network_required: bool = False,
) -> OPIURule:
    return OPIURule(
        rule_id=rule_id,
        report_line="Расходы по основной деятельности",
        report_indicator=indicator,
        disclosure_group=group,
        article=article,
        article_code="",
        source="Журнал проводок МСФО",
        formula_condition="",
        required_analytics=(),
        region_required=region_required,
        network_required=network_required,
        cfo_required=False,
        sales_channel="Основной канал",
        predicates=predicates,
    )


def resolve(resolver: OPIUIndicatorResolver, **overrides):
    values = {
        "disclosure_group": "Административные",
        "article": "Интернет",
        "organization": "Организация",
        "cfo": "ЦФО",
        **overrides,
    }
    return resolver.resolve(**values)


def test_one_group_and_article_resolve_one_indicator():
    result = resolve(OPIUIndicatorResolver([rule("one")]))

    assert result.status == AUTO_MATCH
    assert result.rule and result.rule.report_indicator == "Административные"


def test_same_article_in_different_groups_has_different_business_meaning():
    resolver = OPIUIndicatorResolver(
        [
            rule("admin"),
            rule(
                "production",
                group="Производственные",
                indicator="Производственные",
            ),
        ]
    )

    admin = resolve(resolver)
    production = resolve(resolver, disclosure_group="Производственные")

    assert admin.rule and admin.rule.report_indicator == "Административные"
    assert production.rule and production.rule.report_indicator == "Производственные"


def test_missing_group_requires_attention():
    result = resolve(OPIUIndicatorResolver([rule("one")]), disclosure_group="")

    assert result.status == NOT_FOUND
    assert result.reason == "Не найдена группа раскрытия"


def test_article_is_never_searched_outside_disclosure_group():
    result = resolve(
        OPIUIndicatorResolver([rule("one")]),
        disclosure_group="Производственные",
    )

    assert result.status == NOT_FOUND
    assert result.reason == "Не найдена группа раскрытия"


def test_multiple_rules_are_ambiguous_instead_of_first_selected():
    resolver = OPIUIndicatorResolver(
        [rule("first", indicator="Первый"), rule("second", indicator="Второй")]
    )

    result = resolve(resolver)

    assert result.status == AMBIGUOUS
    assert result.rule is None
    assert result.reason == "Найдено несколько показателей"


def test_formula_condition_changes_result():
    resolver = OPIUIndicatorResolver(
        [
            rule(
                "x",
                indicator="Для X",
                predicates=(FormulaPredicate("organization", "X"),),
            ),
            rule(
                "y",
                indicator="Для Y",
                predicates=(FormulaPredicate("organization", "Y"),),
            ),
        ]
    )

    result = resolve(resolver, organization="Y")

    assert result.status == AUTO_MATCH
    assert result.rule and result.rule.report_indicator == "Для Y"


def test_region_influences_selection():
    resolver = OPIUIndicatorResolver(
        [
            rule(
                "east",
                indicator="Дальний Восток",
                predicates=(FormulaPredicate("region", "ДВ"),),
                region_required=True,
            ),
            rule(
                "west",
                indicator="Запад",
                predicates=(FormulaPredicate("region", "Запад"),),
                region_required=True,
            ),
        ]
    )

    result = resolve(resolver, region="ДВ")

    assert result.status == AUTO_MATCH
    assert result.rule and result.rule.report_indicator == "Дальний Восток"


def test_network_influences_selection():
    resolver = OPIUIndicatorResolver(
        [
            rule(
                "retail",
                indicator="Розница",
                predicates=(FormulaPredicate("network", "Розница"),),
                network_required=True,
            ),
            rule(
                "wholesale",
                indicator="Опт",
                predicates=(FormulaPredicate("network", "Опт"),),
                network_required=True,
            ),
        ]
    )

    result = resolve(resolver, network="Опт")

    assert result.status == AUTO_MATCH
    assert result.rule and result.rule.report_indicator == "Опт"


def test_case_difference_and_contains_are_not_corrected():
    resolver = OPIUIndicatorResolver([rule("one")])

    case = resolve(resolver, article="интернет")
    contains = resolve(resolver, article="Интернет резервный")

    assert case.status == NOT_FOUND
    assert contains.status == NOT_FOUND


def test_conflicting_article_code_is_not_ignored():
    configured = rule("one")
    configured = OPIURule(**{**configured.__dict__, "article_code": "ERP-001"})

    result = resolve(
        OPIUIndicatorResolver([configured]),
        article_code="ERP-OTHER",
    )

    assert result.status == NOT_FOUND
    assert result.reason == "Статья не найдена внутри группы раскрытия"


def test_formula_parser_keeps_hierarchy_and_condition():
    parsed = parse_formula_rows(
        [
            FormulaInputRow(2, "Расходы", "[TOTAL]", 0),
            FormulaInputRow(3, "Административные", "[ADMIN]", 2),
            FormulaInputRow(4, "Интернет", "?([X] <> 0,[NET],0)", 4),
        ]
    )

    internet = parsed[-1]
    assert internet.report_line == "Расходы"
    assert internet.disclosure_group == "Административные"
    assert internet.article == "Интернет"
    assert internet.formula_condition == "[X] <> 0"
    assert internet.source_tokens == ("X", "NET")


def test_expense_group_can_be_the_exact_disclosure_group():
    resolver = OPIUIndicatorResolver(
        [rule("group", group="Компенсации", article="Компенсации ЖЦ", indicator="Компенсации")]
    )

    result = resolve(
        resolver,
        disclosure_group="Административные расходы",
        disclosure_hierarchy=(
            "Административные расходы",
            "Компенсации",
            "Компенсации ЖЦ",
        ),
        article="Компенсации ЖЦ",
    )

    assert result.status == AUTO_MATCH
    assert result.rule and result.rule.report_indicator == "Компенсации"


def test_deepest_exact_disclosure_group_has_priority():
    resolver = OPIUIndicatorResolver(
        [
            rule("root", group="Административные", indicator="Корневой"),
            rule("nested", group="Связь", indicator="Связь"),
        ]
    )

    result = resolve(
        resolver,
        disclosure_group="Административные",
        disclosure_hierarchy=("Административные", "Связь", "Интернет"),
    )

    assert result.status == AUTO_MATCH
    assert result.rule and result.rule.report_indicator == "Связь"


def test_exact_article_code_has_priority_over_blank_code_rule():
    blank = rule("blank", indicator="Без кода")
    coded = OPIURule(**{**rule("coded", indicator="По коду").__dict__, "article_code": "ERP-001"})

    result = resolve(
        OPIUIndicatorResolver([blank, coded]),
        article_code="ERP-001",
    )

    assert result.status == AUTO_MATCH
    assert result.rule and result.rule.report_indicator == "По коду"


def test_source_parser_does_not_promote_second_dimension_to_disclosure_group():
    groups, articles, predicates, unsupported = _parse_source_condition(
        "С1 В ИЕРАРХИИ(Административные) И С2 В (Опт, Розница)"
    )

    assert groups == ("Административные",)
    assert articles == ()
    assert predicates == ()
    assert unsupported == ("С2 В (Опт, Розница)",)


def test_source_parser_supports_exact_article_filters_only():
    groups, articles, predicates, unsupported = _parse_source_condition(
        "КС1 В ИЕРАРХИИ(Коммерческие) И С1 В (Реклама, Маркетинг)"
    )

    assert groups == ("Коммерческие",)
    assert articles == ("Реклама", "Маркетинг")
    assert predicates == ()
    assert unsupported == ()


def test_source_parser_keeps_unknown_operator_fail_closed():
    groups, articles, predicates, unsupported = _parse_source_condition(
        "С1=Интернет И Подразделение<>ГК Кредиты"
    )

    assert groups == ()
    assert articles == ("Интернет",)
    assert predicates == ()
    assert unsupported == ("Подразделение<>ГК Кредиты",)
