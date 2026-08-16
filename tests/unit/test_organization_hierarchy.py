import pytest

from excel_transform_1c.adapters.references import (
    organization_nodes,
    parse_reference_workbook,
)
from excel_transform_1c.core.organization_hierarchy import (
    DEPARTMENT_NODE_TYPE,
    ERPOrganizationHierarchyReader,
    ExactOrganizationHierarchyResolver,
    ExactOrganizationReferenceResolver,
    MISSING_ERP_ELEMENT_CODE_REASON,
    ORGANIZATION_NODE_TYPE,
    PARENT_NODE_TYPE,
)
from tests.helpers.workbooks import erp_organization_hierarchy_bytes


def _nodes(**workbook_options):
    return organization_nodes(
        parse_reference_workbook(
            erp_organization_hierarchy_bytes(**workbook_options),
            "organizations",
        )
    )


def _resolution(nodes=None):
    resolver = ExactOrganizationHierarchyResolver(
        nodes if nodes is not None else _nodes()
    )
    return resolver.resolve(
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


def _acceptance_reader(
    *,
    cfo_name: str = "ХП Отдел по управлению персоналом",
    source_department: str = "Департамент по управлению персоналом",
    cfo_code: str = "000000196",
    organization_name: str = "ООО Айс Юнион",
    organization_code: str = "000000001",
) -> ERPOrganizationHierarchyReader:
    return ERPOrganizationHierarchyReader(
        _nodes(
            cfo_name=cfo_name,
            source_department=source_department,
            cfo_code=cfo_code,
            organization_name=organization_name,
            organization_code=organization_code,
        )
    )


def test_find_exact_department() -> None:
    reader = _acceptance_reader()

    department = reader.find_exact_department("ХП Отдел по управлению персоналом")

    assert department is not None
    assert department.id == "000000196"
    assert department.name == "ХП Отдел по управлению персоналом"
    assert department.code == "000000196"
    assert department.level == 2
    assert department.type == DEPARTMENT_NODE_TYPE
    assert reader.find_exact_department("ХП Отдел") is None
    assert reader.find_exact_department("хп Отдел по управлению персоналом") is None


def test_find_exact_top_level_element() -> None:
    reader = _acceptance_reader(
        cfo_name="Б_АЮ Отдел обеспечения",
        source_department="Департамент обеспечения",
        cfo_code="000000184",
        organization_name="АЮ",
        organization_code="000000003",
    )

    node = reader.find_exact_element("АЮ")

    assert node is not None
    assert node.name == "АЮ"
    assert node.code == "000000003"
    assert node.type == ORGANIZATION_NODE_TYPE
    assert reader.find_exact_element("А") is None


def test_find_exact_department_rejects_ambiguous_exact_name() -> None:
    first = _nodes(
        cfo_name="Общий отдел",
        source_department="Первый департамент",
        cfo_code="000000501",
        organization_name="Организация 1",
        organization_code="000000601",
    )
    second = _nodes(
        cfo_name="Общий отдел",
        source_department="Второй департамент",
        cfo_code="000000502",
        organization_name="Организация 2",
        organization_code="000000602",
    )
    reader = ERPOrganizationHierarchyReader([*first, *second])

    assert reader.find_exact_department("Общий отдел") is None
    assert ExactOrganizationReferenceResolver(reader).resolve("Общий отдел") is None


def test_parent_traversal() -> None:
    reader = _acceptance_reader()
    department = reader.find_exact_department("ХП Отдел по управлению персоналом")

    assert department is not None
    parents = reader.parent_traversal(department)
    assert [(node.name, node.level, node.type) for node in parents] == [
        ("Департамент по управлению персоналом", 1, PARENT_NODE_TYPE),
        ("ООО Айс Юнион", 0, ORGANIZATION_NODE_TYPE),
    ]
    assert department.parent_id == parents[0].id
    assert parents[0].parent_id == parents[1].id


def test_root_organization_resolution() -> None:
    reader = _acceptance_reader()
    department = reader.find_exact_department("ХП Отдел по управлению персоналом")

    assert department is not None
    root = reader.root_organization(department)
    assert root is not None
    assert root.id == "000000001"
    assert root.name == "ООО Айс Юнион"
    assert root.code == "000000001"
    assert root.parent_id is None
    assert root.level == 0
    assert root.type == ORGANIZATION_NODE_TYPE


def test_reference_resolver_returns_exact_codes() -> None:
    reader = _acceptance_reader(
        cfo_name="АЮ Отдел обеспечения",
        source_department="Департамент обеспечения",
        cfo_code="000000173",
    )

    resolution = ExactOrganizationReferenceResolver(reader).resolve(
        "АЮ Отдел обеспечения"
    )

    assert resolution is not None
    assert resolution.department == "АЮ Отдел обеспечения"
    assert resolution.cfo == "АЮ Отдел обеспечения"
    assert resolution.cfo_code == "000000173"
    assert resolution.organization == "ООО Айс Юнион"
    assert resolution.organization_code == "000000001"
