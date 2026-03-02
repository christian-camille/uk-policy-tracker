from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_node_entity"),
        Index("ix_node_entity", "entity_type", "entity_id"),
        {"schema": "gold"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column()
    label: Mapped[str] = mapped_column(String(512))
    properties: Mapped[dict | None] = mapped_column(JSONB, default=None)


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        Index("ix_edge_source_type", "source_node_id", "edge_type"),
        Index("ix_edge_target_type", "target_node_id", "edge_type"),
        {"schema": "gold"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_node_id: Mapped[int] = mapped_column(
        ForeignKey("gold.graph_nodes.id"), index=True
    )
    target_node_id: Mapped[int] = mapped_column(
        ForeignKey("gold.graph_nodes.id"), index=True
    )
    edge_type: Mapped[str] = mapped_column(String(64))
    properties: Mapped[dict | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
