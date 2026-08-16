import json
from importlib.resources import files

from excel_transform_1c.adapters.references import article_indicator_rules
from excel_transform_1c.baselines import (
    OPIU_SUPPORT_KINDS,
    baseline_counts,
    load_baseline_catalogs,
    load_manifest,
)
from excel_transform_1c.core.indicator_matching import (
    INDICATOR_MATCHED,
    INDICATOR_MISSING,
)
from excel_transform_1c.core.indicator_resolvers import SelectionExpenseResolver


def test_all_owner_opiu_sources_are_packaged_with_exact_counts():
    expected = {
        "article_indicators": 215,
        "opiu_formulas": 517,
        "opiu_analytics": 517,
        "regions": 22,
        "sales_networks": 233,
        "opiu_report_indicators": 683,
        "opiu_source_rules": 310,
    }

    assert {kind: baseline_counts()[kind] for kind in expected} == expected
    manifest = load_manifest()
    package = files("excel_transform_1c.baselines")
    for kind in OPIU_SUPPORT_KINDS:
        metadata = manifest["catalogs"][kind]
        payload = json.loads(
            package.joinpath(metadata["file"]).read_text(encoding="utf-8")
        )
        assert len(payload) == expected[kind]


def test_packaged_expense_link_uses_group_and_mxl_hierarchy_filters():
    payload = load_baseline_catalogs()["article_indicators"]
    resolver = SelectionExpenseResolver(article_indicator_rules(payload))

    match = resolver.resolve(
        expense_type="Административные расходы",
        expense_group="Командировочные",
        article_name="Проживание",
    )

    assert match.status == INDICATOR_MATCHED
    assert match.matched_by == "expense_group_formula"
    assert match.rule is not None
    assert match.rule.indicator == "Административные расходы"
    assert "С1 В ИЕРАРХИИ(Административные расходы)" in (
        match.rule.formula_condition
    )
    assert match.rule.sales_channel == ""
    assert match.reason == ""

    wrong_group = resolver.resolve(
        expense_type="Административные расходы",
        expense_group="Связь",
        article_name="Проживание",
    )
    assert wrong_group.status == INDICATOR_MISSING


def test_packaged_mxl_rules_preserve_account_and_hierarchy_selections():
    metadata = load_manifest()["catalogs"]["opiu_source_rules"]
    payload = json.loads(
        files("excel_transform_1c.baselines")
        .joinpath(metadata["file"])
        .read_text(encoding="utf-8")
    )

    candidates = [
        item
        for item in payload
        if item["calculation_destination"] == "Административные расходы сумма"
        and "В ИЕРАРХИИ(Административные расходы)"
        in item["simplified_formula_code"]
    ]
    assert candidates
    assert any(item["account"] == "26" for item in candidates)
    assert all(item["calculation_consumer"] for item in candidates)
