from __future__ import annotations

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.gold import GraphEdge, GraphNode
from app.models.silver import (
    ActivityEvent,
    Bill,
    ContentItem,
    ContentItemOrganisation,
    Division,
    EntityMention,
    Organisation,
    Person,
    Topic,
    WrittenQuestion,
)
from app.schemas.entities import EdgeResponse, EntityDetailResponse, NodeResponse
from app.services.parliament import build_written_question_url

logger = logging.getLogger(__name__)


class GraphService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_node(self, node_id: int) -> GraphNode | None:
        return await self.db.get(GraphNode, node_id)

    async def get_node_by_source(
        self, entity_type: str, entity_id: int
    ) -> GraphNode | None:
        stmt = select(GraphNode).where(
            GraphNode.entity_type == entity_type,
            GraphNode.entity_id == entity_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_entity_detail(self, node_id: int) -> EntityDetailResponse | None:
        node = await self.get_node(node_id)
        if not node:
            return None

        connections = await self._get_connections(node_id)
        return EntityDetailResponse(
            node=NodeResponse.model_validate(node),
            connections=connections,
        )

    async def get_entity_detail_by_source(
        self, entity_type: str, entity_id: int
    ) -> EntityDetailResponse | None:
        node = await self.get_node_by_source(entity_type, entity_id)
        if not node:
            return None
        return await self.get_entity_detail(node.id)

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


class GraphProjectionBuilder:
    """
    Rebuilds the gold graph projection from silver tables.
    Uses a synchronous session for local refresh execution.
    """

    def __init__(self, db: Session):
        self.db = db

    def rebuild(self) -> dict[str, int]:
        """
        Full rebuild: truncate gold tables, create nodes from every silver
        entity type, then create edges for all known relationships.
        Returns counts of nodes and edges created.
        """
        # Truncate in correct order (edges reference nodes)
        self.db.execute(text("TRUNCATE gold.graph_edges CASCADE"))
        self.db.execute(text("TRUNCATE gold.graph_nodes CASCADE"))
        self.db.flush()

        # Build node map: (entity_type, entity_id) -> graph_node.id
        node_map: dict[tuple[str, int], int] = {}

        node_map.update(self._create_nodes_for(Topic, "topic", "id", "label"))
        node_map.update(self._create_nodes_for(ContentItem, "content_item", "id", "title"))
        node_map.update(self._create_nodes_for(Organisation, "organisation", "id", "title"))
        node_map.update(
            self._create_nodes_for(
                Person,
                "person",
                "id",
                "name_display",
                properties_fn=lambda p: {
                    "party": p.party,
                    "house": p.house,
                    "constituency": p.constituency,
                },
            )
        )
        node_map.update(
            self._create_nodes_for(
                Bill,
                "bill",
                "id",
                "short_title",
                properties_fn=lambda b: {
                    "current_house": b.current_house,
                    "current_stage": b.current_stage,
                    "is_act": b.is_act,
                },
            )
        )
        node_map.update(
            self._create_nodes_for(
                WrittenQuestion,
                "question",
                "id",
                "heading",
                properties_fn=self._question_properties,
            )
        )
        node_map.update(
            self._create_nodes_for(
                Division,
                "division",
                "id",
                "title",
                properties_fn=lambda d: {
                    "aye_count": d.aye_count,
                    "no_count": d.no_count,
                    "house": d.house,
                },
            )
        )
        self.db.flush()

        # Create edges
        edge_count = 0
        edge_count += self._create_published_by_edges(node_map)
        edge_count += self._create_about_topic_edges(node_map)
        edge_count += self._create_asked_by_edges(node_map)
        edge_count += self._create_mentions_edges(node_map)

        self.db.flush()

        stats = {"nodes": len(node_map), "edges": edge_count}
        logger.info("Graph projection rebuilt: %s", stats)
        return stats

    def _create_nodes_for(
        self,
        model,
        entity_type: str,
        id_attr: str,
        label_attr: str,
        properties_fn=None,
    ) -> dict[tuple[str, int], int]:
        """Create GraphNode rows from a silver table and return the mapping."""
        entities = self.db.execute(select(model)).scalars().all()
        mapping: dict[tuple[str, int], int] = {}

        for entity in entities:
            entity_id = getattr(entity, id_attr)
            label = getattr(entity, label_attr) or f"{entity_type}#{entity_id}"
            props = properties_fn(entity) if properties_fn else None

            node = GraphNode(
                entity_type=entity_type,
                entity_id=entity_id,
                label=label,
                properties=props,
            )
            self.db.add(node)
            self.db.flush()
            mapping[(entity_type, entity_id)] = node.id

        return mapping

    def _question_properties(self, question: WrittenQuestion) -> dict[str, str | None]:
        asking_member_name = None
        if question.asking_member_id is not None:
            asking_member_name = self.db.execute(
                select(Person.name_display).where(
                    Person.parliament_id == question.asking_member_id
                )
            ).scalar_one_or_none()

        return {
            "uin": question.uin,
            "house": question.house,
            "question_text": question.question_text,
            "asked_by": asking_member_name,
            "answering_body": question.answering_body,
            "answer_text": question.answer_text,
            "answer_source_url": question.answer_source_url,
            "parliament_url": build_written_question_url(
                question.date_tabled, question.uin
            ),
            "status": "answered" if question.date_answered else "tabled",
            "date_tabled": question.date_tabled.isoformat() if question.date_tabled else None,
            "date_answered": question.date_answered.isoformat() if question.date_answered else None,
        }

    def _create_published_by_edges(
        self, node_map: dict[tuple[str, int], int]
    ) -> int:
        """content_item -> organisation via content_item_organisations junction."""
        links = self.db.execute(select(ContentItemOrganisation)).scalars().all()
        count = 0
        for link in links:
            src = node_map.get(("content_item", link.content_item_id))
            tgt = node_map.get(("organisation", link.organisation_id))
            if src and tgt:
                self.db.add(
                    GraphEdge(
                        source_node_id=src,
                        target_node_id=tgt,
                        edge_type="PUBLISHED_BY",
                    )
                )
                count += 1
        return count

    def _create_about_topic_edges(
        self, node_map: dict[tuple[str, int], int]
    ) -> int:
        """entity -> topic derived from activity_events."""
        events = self.db.execute(
            select(
                ActivityEvent.source_entity_type,
                ActivityEvent.source_entity_id,
                ActivityEvent.topic_id,
            )
            .where(ActivityEvent.topic_id.isnot(None))
            .distinct()
        ).all()

        count = 0
        for source_entity_type, source_entity_id, topic_id in events:
            src = node_map.get((source_entity_type, source_entity_id))
            tgt = node_map.get(("topic", topic_id))
            if src and tgt:
                self.db.add(
                    GraphEdge(
                        source_node_id=src,
                        target_node_id=tgt,
                        edge_type="ABOUT_TOPIC",
                    )
                )
                count += 1
        return count

    def _create_asked_by_edges(
        self, node_map: dict[tuple[str, int], int]
    ) -> int:
        """question -> person via asking_member_id."""
        questions = (
            self.db.execute(
                select(WrittenQuestion).where(
                    WrittenQuestion.asking_member_id.isnot(None)
                )
            )
            .scalars()
            .all()
        )

        count = 0
        for q in questions:
            src = node_map.get(("question", q.id))
            # asking_member_id is parliament_id; find the Person's id
            person = self.db.execute(
                select(Person).where(Person.parliament_id == q.asking_member_id)
            ).scalar_one_or_none()
            if person:
                tgt = node_map.get(("person", person.id))
                if src and tgt:
                    self.db.add(
                        GraphEdge(
                            source_node_id=src,
                            target_node_id=tgt,
                            edge_type="ASKED_BY",
                        )
                    )
                    count += 1
        return count

    def _create_mentions_edges(
        self, node_map: dict[tuple[str, int], int]
    ) -> int:
        """content_item -> person/bill/org via NLP-extracted entity_mentions."""
        mentions = self.db.execute(select(EntityMention)).scalars().all()

        count = 0
        for m in mentions:
            src = node_map.get(("content_item", m.content_item_id))
            tgt = node_map.get((m.mentioned_entity_type, m.mentioned_entity_id))
            if src and tgt:
                self.db.add(
                    GraphEdge(
                        source_node_id=src,
                        target_node_id=tgt,
                        edge_type="MENTIONS",
                        properties={"confidence": m.confidence},
                    )
                )
                count += 1
        return count
