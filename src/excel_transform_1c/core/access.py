from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from .models import OrganizationNode


def effective_organization_nodes(
    nodes: Iterable[OrganizationNode], delegated_node_ids: Iterable[str]
) -> list[OrganizationNode]:
    ordered = list(nodes)
    by_parent: dict[str | None, list[OrganizationNode]] = defaultdict(list)
    by_id = {node.node_id: node for node in ordered}
    for node in ordered:
        by_parent[node.parent_id].append(node)

    allowed: set[str] = set()
    queue = deque(node_id for node_id in delegated_node_ids if node_id in by_id)
    while queue:
        node_id = queue.popleft()
        if node_id in allowed:
            continue
        allowed.add(node_id)
        queue.extend(child.node_id for child in by_parent.get(node_id, []))
    return [node for node in ordered if node.node_id in allowed]
