export interface TopicSummary {
  id: number;
  slug: string;
  label: string;
  search_queries: string[];
  is_global: boolean;
  last_refreshed_at: string | null;
  new_items_count: number;
}

export type TimelineEventType =
  | "govuk_publication"
  | "bill_stage"
  | "question_tabled"
  | "question_answered"
  | "division_held";

export type TimelineSourceType = "content_item" | "bill" | "question" | "division";

export interface TimelineQueryParams {
  since?: string;
  until?: string;
  eventTypes?: TimelineEventType[];
  sourceEntityTypes?: TimelineSourceType[];
  q?: string;
  limit?: number;
  offset?: number;
}

export interface TimelineEvent {
  id: number;
  event_type: TimelineEventType;
  event_date: string;
  title: string;
  summary: string | null;
  source_url: string | null;
  source_entity_type: string;
  source_entity_id: number;
  question_uin?: string | null;
  question_text?: string | null;
  question_house?: string | null;
  question_date_tabled?: string | null;
  question_date_answered?: string | null;
  asking_member_name?: string | null;
  question_answer_text?: string | null;
  question_answer_source_url?: string | null;
  question_official_url?: string | null;
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

export interface ActorProperties {
  party?: string | null;
  constituency?: string | null;
  [key: string]: unknown;
}

export interface Actor {
  id: number;
  label: string;
  entity_id: number;
  properties: ActorProperties | null;
  connection_count: number;
}

export interface GraphEdge {
  edge_type: string;
  direction: "outgoing" | "incoming";
  properties?: Record<string, unknown> | null;
  connected_node: GraphNode;
}

export interface EntityDetail {
  node: GraphNode;
  connections: GraphEdge[];
}

export interface RefreshGovUkResult {
  topic_id: number;
  items_ingested?: number;
  status?: string;
  error?: string;
}

export interface RefreshParliamentResult {
  topic_id: number;
  bills?: number;
  questions?: number;
  divisions?: number;
  status?: string;
  error?: string;
}

export interface RefreshEventsResult {
  topic_id: number;
  events_created: number;
}

export interface RefreshMentionsResult {
  topic_id: number;
  mentions_created: number;
}

export interface RefreshGraphResult {
  nodes: number;
  edges: number;
}

export interface RefreshSummary {
  govuk: RefreshGovUkResult;
  parliament: RefreshParliamentResult;
  events: RefreshEventsResult;
  mentions: RefreshMentionsResult;
  graph: RefreshGraphResult;
}

export interface RefreshTopicResponse {
  status: string;
  topic_id: number;
  result: RefreshSummary;
}
