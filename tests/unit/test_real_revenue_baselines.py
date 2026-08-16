import json
from importlib.resources import files

from excel_transform_1c.adapters.references import article_indicator_rules
from excel_transform_1c.baselines import (
    OPIU_SUPPORT_KINDS,
    load_baseline_catalogs,
    load_manifest,
)
from excel_transform_1c.core.indicator_matching import (
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
)
from excel_transform_1c.core.indicator_resolvers import RevenueResolver
from scripts.build_opiu_baselines import (
    derive_revenue_indicators,
    quantity_derivation_audit,
)


EXPECTED_REVENUE_CHANNELS = {
    "Опт",
    "Розница",
    "HoReCa",
    "Сети ДВ",
    "Сети Федеральные",
    "Дискаунтеры ДВ",
    "Дискаунтеры Федеральные",
}


def _all_catalogs():
    catalogs = load_baseline_catalogs()
    manifest = load_manifest()
    package = files("excel_transform_1c.baselines")
    for kind in OPIU_SUPPORT_KINDS:
        catalogs[kind] = json.loads(
            package.joinpath(manifest["catalogs"][kind]["file"]).read_text(
                encoding="utf-8"
            )
        )
    return catalogs


def test_real_revenue_rules_are_exact_and_source_proven():
    catalogs = _all_catalogs()
    derived, audit = derive_revenue_indicators(
        catalogs["opiu_report_indicators"],
        catalogs["opiu_formulas"],
        catalogs["opiu_analytics"],
        catalogs["opiu_source_rules"],
    )

    assert audit == {
        "candidates": 7,
        "derived": 7,
        "unresolved": 0,
        "ambiguous": 0,
    }
    assert {rule["article_name"] for rule in derived} == EXPECTED_REVENUE_CHANNELS
    assert all(rule["indicator_type"] == "REVENUE" for rule in derived)
    assert all(
        rule["revenue_group"] == "Выручка_продажи внешние"
        for rule in derived
    )
    assert all(rule["indicator"] == rule["article_name"] for rule in derived)
    assert all(rule["sales_channel"] == rule["article_name"] for rule in derived)
    assert all(rule["input_sales_channel"] == "" for rule in derived)
    assert all(rule["sales_network"] == "" for rule in derived)
    assert all(rule["formula_condition"].startswith("Ист:") for rule in derived)
    assert all("Пр:" in rule["formula_condition"] for rule in derived)
    assert all(rule["analytics"] == "" for rule in derived)
    assert derived == [
        rule
        for rule in catalogs["article_indicators"]
        if rule["indicator_type"] == "REVENUE"
    ]


def test_packaged_revenue_rule_matches_only_its_complete_exact_key():
    rules = article_indicator_rules(load_baseline_catalogs()["article_indicators"])
    revenue_rules = [rule for rule in rules if rule.indicator_type.value == "REVENUE"]
    assert len(revenue_rules) == 7
    selected = next(rule for rule in revenue_rules if rule.article_name == "HoReCa")
    resolver = RevenueResolver(revenue_rules)

    exact = resolver.resolve(
        revenue_group=selected.revenue_group,
        article_name=selected.article_name,
    )
    changed_case = resolver.resolve(
        revenue_group=selected.revenue_group,
        article_name="horeca",
    )

    assert exact.status == INDICATOR_MATCHED
    assert exact.rule == selected
    assert changed_case.status == INDICATOR_MISSING


def test_quantity_sources_do_not_invent_nomenclature_unit_pairs():
    catalogs = _all_catalogs()

    audit = quantity_derivation_audit(
        catalogs["opiu_formulas"],
        catalogs["opiu_analytics"],
    )
    assert audit == {
        "candidates": 7,
        "derived": 0,
        "unresolved": 7,
        "ambiguous": 0,
    }
    assert not [
        rule
        for rule in catalogs["article_indicators"]
        if rule["indicator_type"] == "QUANTITY"
    ]
