from __future__ import annotations

from dataclasses import dataclass

from .models import OrganizationNode


MISSING_ERP_ELEMENT_CODE_REASON = "В ERP-справочнике отсутствует код элемента"


@dataclass(frozen=True)
class OrganizationHierarchyResolution:
    organization_unit: str
    organization_unit_code: str
    department: str
    cfo: str
    cfo_code: str
    reason: str | None = None


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

        candidates: dict[str, tuple[OrganizationNode, str]] = {}
        for node in self.nodes:
            candidate_cfo = self._exact_candidate_cfo(
                node,
                organization_unit.name,
                source_department,
            )
            if candidate_cfo is not None:
                candidates[node.node_id] = (node, candidate_cfo)

        if len(candidates) > 1 and source_cfo:
            candidates = {
                node_id: candidate
                for node_id, candidate in candidates.items()
                if candidate[1] == source_cfo
            }
        if len(candidates) != 1:
            return None

        cfo_node, reference_cfo = next(iter(candidates.values()))
        result_cfo = source_cfo or reference_cfo
        missing_code = not organization_unit.code or not cfo_node.code
        return OrganizationHierarchyResolution(
            organization_unit=organization_unit.name,
            organization_unit_code=organization_unit.code,
            department=result_cfo,
            cfo=result_cfo,
            cfo_code=cfo_node.code,
            reason=MISSING_ERP_ELEMENT_CODE_REASON if missing_code else None,
        )

    @staticmethod
    def _exact_candidate_cfo(
        node: OrganizationNode,
        organization_unit_name: str,
        source_department: str,
    ) -> str | None:
        if node.source_department or node.cfo_name or node.organization_unit_name:
            if (
                node.organization_unit_name == organization_unit_name
                and node.source_department == source_department
                and node.cfo_name
            ):
                return node.cfo_name
            return None

        # Backward-compatible exact interpretation of packaged catalogs made
        # before the three ERP enrichment fields were persisted.  Components
        # are compared as complete hierarchy values, never as substrings.
        parts = tuple(part.strip() for part in node.full_path.split(" → "))
        if (
            node.name != source_department
            or len(parts) < 2
            or organization_unit_name not in parts[:-1]
            or parts[-1] != node.name
        ):
            return None
        return parts[-2]
