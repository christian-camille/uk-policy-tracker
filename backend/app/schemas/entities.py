from pydantic import BaseModel, ConfigDict


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    label: str
    properties: dict | None


class EdgeResponse(BaseModel):
    edge_type: str
    direction: str
    connected_node: NodeResponse


class EntityDetailResponse(BaseModel):
    node: NodeResponse
    connections: list[EdgeResponse]
