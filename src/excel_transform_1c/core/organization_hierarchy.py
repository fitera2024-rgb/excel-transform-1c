from __future__ import annotations

from dataclasses import dataclass

from .models import OrganizationHierarchyNode, OrganizationNode


MISSING_ERP_ELEMENT_CODE_REASON = "В ERP-справочнике отсутствует код элемента"

ORGANIZATION_NODE_TYPE = "organization"
PARENT_NODE_TYPE = "parent"
DEPARTMENT_NODE_TYPE = "department"


@dataclass(frozen=True)
class OrganizationReferenceResolution:
    department: str
    cfo: str
    cfo_code: str
    organization: str
    organization_code: str


@dataclass(frozen=True)
class OrganizationHierarchyResolution:
    organization_unit: str
    organization_unit_code: str
    department: str
    cfo: str
    cfo_code: str
    reason: str | None = None


class ERPOrganizationHierarchyReader:
    """Build the exact business tree represented by an ERP organization export.

    A coded ERP row carries three different business values: the abbreviated
    department/CFO name, its descriptive parent, and the legal organization.
    They are deliberately represented as separate nodes so callers can walk
    the hierarchy without parsing display paths or guessing from prefixes.
    """

    def __init__(
        self,
        nodes: list[OrganizationNode],
        organization_node_id: str | None = None,
    ):
        self.reference_nodes = tuple(nodes)
        self.reference_by_id = {node.node_id: node for node in nodes}
        self.organization_node_id = organization_node_id
        self.nodes = self._build_nodes()
        self.by_id = {node.id: node for node in self.nodes}

    def find_exact_element(self, name: str) -> OrganizationHierarchyNode | None:
        candidates = [
            node
            for node in self.nodes
            if node.type != PARENT_NODE_TYPE and node.name == name
        ]
        return candidates[0] if len(candidates) == 1 else None

    def find_exact_department(
        self,
        name: str,
        *,
        parent_name: str | None = None,
    ) -> OrganizationHierarchyNode | None:
        candidates = self.exact_department_candidates(
            name=name,
            parent_name=parent_name,
        )
        return candidates[0] if len(candidates) == 1 else None

    def exact_department_candidates(
        self,
        *,
        name: str | None = None,
        parent_name: str | None = None,
    ) -> tuple[OrganizationHierarchyNode, ...]:
        candidates: list[OrganizationHierarchyNode] = []
        for node in self.nodes:
            if node.type != DEPARTMENT_NODE_TYPE:
                continue
            if name is not None and node.name != name:
                continue
            if parent_name is not None:
                parent = self.by_id.get(node.parent_id or "")
                if parent is None or parent.name != parent_name:
                    continue
            candidates.append(node)
        return tuple(candidates)

    def parent_traversal(
        self,
        node: OrganizationHierarchyNode | str,
    ) -> tuple[OrganizationHierarchyNode, ...]:
        current = self._node(node)
        if current is None:
            return ()

        parents: list[OrganizationHierarchyNode] = []
        seen = {current.id}
        while current.parent_id is not None:
            parent = self.by_id.get(current.parent_id)
            if parent is None or parent.id in seen:
                return ()
            seen.add(parent.id)
            parents.append(parent)
            current = parent
        return tuple(parents)

    def root_organization(
        self,
        node: OrganizationHierarchyNode | str,
    ) -> OrganizationHierarchyNode | None:
        current = self._node(node)
        if current is None:
            return None
        if current.type == ORGANIZATION_NODE_TYPE and current.parent_id is None:
            return current

        parents = self.parent_traversal(current)
        if not parents:
            return None
        root = parents[-1]
        if root.type != ORGANIZATION_NODE_TYPE or root.parent_id is not None:
            return None
        return root

    def _node(
        self,
        node: OrganizationHierarchyNode | str,
    ) -> OrganizationHierarchyNode | None:
        if isinstance(node, OrganizationHierarchyNode):
            return node
        return self.by_id.get(node)

    def _build_nodes(self) -> tuple[OrganizationHierarchyNode, ...]:
        built: dict[str, OrganizationHierarchyNode] = {}
        for reference in self.reference_nodes:
            branch = self._branch_values(reference)
            if branch is None:
                continue
            department_name, parent_name, organization_name = branch
            organization = self._organization_reference(organization_name)
            if organization is None:
                continue

            root = OrganizationHierarchyNode(
                id=organization.node_id,
                name=organization.name,
                code=organization.code,
                parent_id=None,
                level=0,
                type=ORGANIZATION_NODE_TYPE,
            )
            parent = OrganizationHierarchyNode(
                id=f"organization:hierarchy-parent:{reference.node_id}",
                name=parent_name,
                code="",
                parent_id=root.id,
                level=1,
                type=PARENT_NODE_TYPE,
            )
            department = OrganizationHierarchyNode(
                id=reference.node_id,
                name=department_name,
                code=reference.code,
                parent_id=parent.id,
                level=2,
                type=DEPARTMENT_NODE_TYPE,
            )
            self._add_exact_node(built, root)
            self._add_exact_node(built, parent)
            self._add_exact_node(built, department)
        return tuple(built.values())

    def _branch_values(
        self,
        reference: OrganizationNode,
    ) -> tuple[str, str, str] | None:
        if (
            reference.cfo_name
            and reference.source_department
            and reference.organization_unit_name
        ):
            if self.organization_node_id is not None:
                selected = self.reference_by_id.get(self.organization_node_id)
                if selected is None or selected.name != reference.organization_unit_name:
                    return None
            return (
                reference.cfo_name,
                reference.source_department,
                reference.organization_unit_name,
            )

        # Packaged catalogs created before the three explicit ERP fields were
        # persisted can be interpreted only inside an explicitly selected
        # organization branch. Full path components are compared exactly.
        selected = self.reference_by_id.get(self.organization_node_id or "")
        if selected is None or reference.node_id == selected.node_id:
            return None
        parts = tuple(part.strip() for part in reference.full_path.split(" → "))
        if (
            len(parts) < 2
            or parts[-1] != reference.name
            or selected.name not in parts[:-1]
        ):
            return None
        return (parts[-2], reference.name, selected.name)

    def _organization_reference(self, name: str) -> OrganizationNode | None:
        if self.organization_node_id is not None:
            selected = self.reference_by_id.get(self.organization_node_id)
            if selected is None or selected.name != name:
                return None
            return selected

        candidates = [node for node in self.reference_nodes if node.name == name]
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            return None
        return OrganizationNode(
            node_id=f"organization:path:{name}",
            code="",
            name=name,
            parent_id=None,
            full_path=name,
        )

    @staticmethod
    def _add_exact_node(
        built: dict[str, OrganizationHierarchyNode],
        node: OrganizationHierarchyNode,
    ) -> None:
        existing = built.get(node.id)
        if existing is not None and existing != node:
            raise ValueError(
                "ERP-иерархия содержит конфликтующий узел с exact id: "
                f"{node.id}"
            )
        built[node.id] = node


class ExactOrganizationReferenceResolver:
    def __init__(self, hierarchy: ERPOrganizationHierarchyReader):
        self.hierarchy = hierarchy

    def resolve(self, department: str) -> OrganizationReferenceResolution | None:
        node = self.hierarchy.find_exact_element(department)
        if node is None:
            return None
        return self.resolve_node(node)

    def resolve_node(
        self,
        node: OrganizationHierarchyNode,
    ) -> OrganizationReferenceResolution | None:
        root = self.hierarchy.root_organization(node)
        if root is None:
            return None
        return OrganizationReferenceResolution(
            department=node.name,
            cfo=node.name,
            cfo_code=node.code,
            organization=root.name,
            organization_code=root.code,
        )


class ExactOrganizationHierarchyResolver:
    """Resolve ERP organization fields from one exact hierarchy branch.

    The real ERP export relates a source department to one CFO element under
    an explicitly named organization unit.  No display-name shortening,
    substring search, case folding, or first-candidate fallback is used.
    """

    def __init__(self, nodes: list[OrganizationNode]):
        self.nodes = nodes
        self.by_id = {node.node_id: node for node in nodes}

    def resolve(
        self,
        organization_node_id: str,
        source_department: str,
        source_cfo: str,
    ) -> OrganizationHierarchyResolution | None:
        organization_unit = self.by_id.get(organization_node_id)
        if organization_unit is None or not source_department:
            return None

        hierarchy = ERPOrganizationHierarchyReader(self.nodes, organization_node_id)
        candidates = hierarchy.exact_department_candidates(
            name=source_cfo or None,
            parent_name=source_department,
        )
        if len(candidates) != 1:
            return None

        reference = ExactOrganizationReferenceResolver(hierarchy).resolve_node(
            candidates[0]
        )
        if reference is None:
            return None
        missing_code = not reference.organization_code or not reference.cfo_code
        return OrganizationHierarchyResolution(
            organization_unit=reference.organization,
            organization_unit_code=reference.organization_code,
            department=reference.department,
            cfo=reference.cfo,
            cfo_code=reference.cfo_code,
            reason=MISSING_ERP_ELEMENT_CODE_REASON if missing_code else None,
        )
