from typing import Dict, Any, Optional, List

from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.schemas.cognitive_twin import (
    CognitiveTwinGetStatusArgs,
    CognitiveTwinQueryGraphArgs,
    CognitiveTwinIngestEpisodeArgs,
    CognitiveTwinPruneArgs,
    EpisodicNodeType,
)
from services.backend.cognitive_twin import cognitive_twin_manager


@registry.register(
    name="cognitive_twin_get_status",
    tier=0,
    description="Inspect autobiographical cognitive twin status, graph node counts, and projected anticipations (Read-Only)",
    args_schema=CognitiveTwinGetStatusArgs,
    preview_fn=lambda args: "Querying cognitive twin state and top anticipations (Tier 0 read-only)",
)
def cognitive_twin_get_status(include_anticipations: bool = True, **kwargs) -> Dict[str, Any]:
    """Get cognitive twin telemetry and top anticipations."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: cognitive twin query blocked.")
    return cognitive_twin_manager.get_status(include_anticipations=include_anticipations).model_dump()


@registry.register(
    name="cognitive_twin_query_graph",
    tier=0,
    description="Query episodic life-graph nodes by node type or text label (Read-Only)",
    args_schema=CognitiveTwinQueryGraphArgs,
    preview_fn=lambda args: f"Querying cognitive life-graph (type={args.get('node_type')}, label='{args.get('label_query')}')",
)
def cognitive_twin_query_graph(
    node_type: Optional[EpisodicNodeType] = None,
    label_query: Optional[str] = None,
    limit: int = 20,
    **kwargs,
) -> Dict[str, Any]:
    """Query nodes in the episodic knowledge graph."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: cognitive twin query blocked.")
    nodes = cognitive_twin_manager.query_graph(node_type=node_type, label_query=label_query, limit=limit)
    return {"nodes": [n.model_dump() for n in nodes], "count": len(nodes)}


def _preview_ingest_episode(args: Dict[str, Any]) -> str:
    return (
        f"Ingest episodic activity '{args.get('activity_label')}' (type={args.get('node_type', 'activity')}) "
        f"with related labels: {args.get('related_labels', [])}"
    )


@registry.register(
    name="cognitive_twin_ingest_episode",
    tier=1,
    description="Ingest an episodic interaction trace or habit node into the personal life-graph (Tier 1 Preview)",
    args_schema=CognitiveTwinIngestEpisodeArgs,
    preview_fn=_preview_ingest_episode,
)
def cognitive_twin_ingest_episode(
    activity_label: str,
    node_type: EpisodicNodeType = EpisodicNodeType.ACTIVITY,
    related_labels: Optional[List[str]] = None,
    attributes: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Ingest episodic trace into cognitive life-graph."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: cognitive twin ingestion blocked.")
    node = cognitive_twin_manager.ingest_episode(
        activity_label=activity_label,
        node_type=node_type,
        related_labels=related_labels,
        attributes=attributes,
    )
    return {"status": "ingested", "node": node.model_dump()}


def _preview_prune_graph(args: Dict[str, Any]) -> str:
    return f"Prune cognitive life-graph nodes with affinity weight below {args.get('min_affinity_weight', 0.10)}"


@registry.register(
    name="cognitive_twin_prune_graph",
    tier=1,
    description="Prune obsolete or low-affinity nodes from the episodic life-graph (Tier 1 Preview)",
    args_schema=CognitiveTwinPruneArgs,
    preview_fn=_preview_prune_graph,
)
def cognitive_twin_prune_graph(
    min_affinity_weight: float = 0.10,
    **kwargs,
) -> Dict[str, Any]:
    """Prune low-affinity nodes from the graph."""
    if guardian.is_halted:
        raise PermissionError("Guardian kill switch is active: graph pruning blocked.")
    deleted = cognitive_twin_manager.prune_graph(min_affinity_weight=min_affinity_weight)
    return {"status": "pruned", "deleted_nodes_count": deleted}
