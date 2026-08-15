import pytest

from excel_transform_1c.adapters.references import (
    organization_nodes,
    parse_reference_workbook,
)
from excel_transform_1c.core.organization_hierarchy import (
    MISSING_ERP_ELEMENT_CODE_REASON,
    ExactOrganizationHierarchyResolver,
)
from tests.helpers.workbooks import erp_organization_hierarchy_bytes


def _nodes():
    return organization_nodes(
        parse_reference_workbook(
            erp_organization_hierarchy_bytes(),
            "organizations",
        )
    )


def _resolution(nodes=None):
    return ExactOrganizationHierarchyResolver(nodes if nodes is not None else _nodes()).resolve(
        "000000001",
        "Административный департамент",
        "АЮ Административный Отдел",
    )


def test_cfo_code_resolution() -> None:
    resolution = _resolution()

    assert resolution is not None
    assert resolution.department == "АЮ Административный Отдел"
    assert resolution.cfo == "АЮ Административный Отдел"
    assert resolution.cfo_code == "000000173"


def test_org_unit_code_resolution() -> None:
    resolution = _resolution()

    assert resolution is not None
    assert resolution.organization_unit == 'ООО "Айс Юнион"'
    assert resolution.organization_unit_code == "000000001"


def test_real_erp_hierarchy_fields_are_preserved_for_exact_resolution() -> None:
    cfo = next(node for node in _nodes() if node.node_id == "000000173")

    assert cfo.source_department == "Административный департамент"
    assert cfo.cfo_name == "АЮ Административный Отдел"
    assert cfo.organization_unit_name == 'ООО "Айс Юнион"'


@pytest.mark.parametrize(
    ("organization_node_id", "department"),
    [
        ("000000001", "Административный"),
        ("000000001", "административный департамент"),
        ("000000173", "Административный департамент"),
    ],
)
def test_organization_resolution_does_not_guess(
    organization_node_id: str,
    department: str,
) -> None:
    assert (
        ExactOrganizationHierarchyResolver(_nodes()).resolve(
            organization_node_id,
            department,
            "АЮ Административный Отдел",
        )
        is None
    )


def test_exact_hierarchy_with_missing_code_requires_attention() -> None:
    nodes = organization_nodes(
        parse_reference_workbook(
            erp_organization_hierarchy_bytes(cfo_code=""),
            "organizations",
        )
    )

    resolution = _resolution(nodes)

    assert resolution is not None
    assert resolution.cfo_code == ""
    assert resolution.reason == MISSING_ERP_ELEMENT_CODE_REASON
