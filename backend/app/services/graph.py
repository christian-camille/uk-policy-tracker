from sqlalchemy import select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gold import GraphEdge, GraphNode
from app.schemas.entities import EdgeResponse, EntityDetailResponse, NodeResponse


class GraphService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_node(self, node_id: int) -> GraphNode | None:
        return await self.db.get(GraphNode, node_id)

    async def get_entity_detail(self, node_id: int) -> EntityDetailResponse | None:
        node = await self.get_node(node_id)
        if not node:
            return None

        connections = await self._get_connections(node_id)
        return EntityDetailResponse(
            node=NodeResponse.model_validate(node),
            connections=connections,
        )

    async def _get_connections(self, node_id: int) -> list[EdgeResponse]:
        # Outgoing edges
        outgoing_stmt = (
            select(GraphEdge, GraphNode)
            .join(GraphNode, GraphEdge.target_node_id == GraphNode.id)
            .where(GraphEdge.source_node_id == node_id)
        )
        # Incoming edges
        incoming_stmt = (
            select(GraphEdge, GraphNode)
            .join(GraphNode, GraphEdge.source_node_id == GraphNode.id)
            .where(GraphEdge.target_node_id == node_id)
        )

        connections: list[EdgeResponse] = []

        outgoing_result = await self.db.execute(outgoing_stmt)
        for edge, connected_node in outgoing_result:
            connections.append(
                EdgeResponse(
                    edge_type=edge.edge_type,
                    direction="outgoing",
                    connected_node=NodeResponse.model_validate(connected_node),
                )
            )

        incoming_result = await self.db.execute(incoming_stmt)
        for edge, connected_node in incoming_result:
            connections.append(
                EdgeResponse(
                    edge_type=edge.edge_type,
                    direction="incoming",
                    connected_node=NodeResponse.model_validate(connected_node),
                )
            )

        return connections

    async def get_key_actors(self, topic_id: int, limit: int = 10) -> list[dict]:
        """Find persons most connected to entities related to a topic."""
        from sqlalchemy import func, text

        stmt = text("""
            WITH topic_entities AS (
                SELECT gn.id AS node_id
                FROM gold.graph_nodes gn
                JOIN gold.graph_edges ge ON ge.source_node_id = gn.id
                JOIN gold.graph_nodes topic_node ON ge.target_node_id = topic_node.id
                WHERE topic_node.entity_type = 'topic'
                  AND topic_node.entity_id = :topic_id
                  AND ge.edge_type = 'ABOUT_TOPIC'
            ),
            person_connections AS (
                SELECT
                    pn.id,
                    pn.label,
                    pn.entity_id,
                    pn.properties,
                    COUNT(*) AS connection_count
                FROM gold.graph_nodes pn
                JOIN gold.graph_edges pe
                    ON pn.id = pe.source_node_id OR pn.id = pe.target_node_id
                WHERE pn.entity_type = 'person'
                  AND (
                      pe.source_node_id IN (SELECT node_id FROM topic_entities)
                   OR pe.target_node_id IN (SELECT node_id FROM topic_entities)
                  )
                GROUP BY pn.id, pn.label, pn.entity_id, pn.properties
                ORDER BY connection_count DESC
                LIMIT :limit
            )
            SELECT * FROM person_connections
        """)
        result = await self.db.execute(stmt, {"topic_id": topic_id, "limit": limit})
        return [dict(row._mapping) for row in result]
