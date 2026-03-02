export interface TopicSummary {
  id: number;
  slug: string;
  label: string;
  last_refreshed_at: string | null;
  new_items_count: number;
}

export interface TimelineEvent {
  id: number;
  event_type:
    | "govuk_publication"
    | "bill_stage"
    | "question_tabled"
    | "question_answered"
    | "division_held";
  event_date: string;
  title: string;
  summary: string | null;
  source_url: string | null;
  source_entity_type: string;
  source_entity_id: number;
}

export interface TimelineResponse {
  topic_id: number;
  events: TimelineEvent[];
  total: number;
  has_more: boolean;
}

export interface GraphNode {
  id: number;
  entity_type: string;
  entity_id: number;
  label: string;
  properties: Record<string, unknown> | null;
}

export interface GraphEdge {
  edge_type: string;
  direction: "outgoing" | "incoming";
  connected_node: GraphNode;
}

export interface EntityDetail {
  node: GraphNode;
  connections: GraphEdge[];
}
