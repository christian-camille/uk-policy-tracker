export interface TopicSummary {
  id: number;
  slug: string;
  label: string;
  search_queries: string[];
  keyword_groups: string[][];
  excluded_keywords: string[];
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

export interface RefreshAllTopicsResult {
  topic_id: number;
  result: RefreshSummary;
}

export interface RefreshAllTopicsResponse {
  status: string;
  topics: number;
  results: RefreshAllTopicsResult[];
}

// ── MP Tracking ──────────────────────────────────────────────────────

export interface MemberSearchResult {
  parliament_id: number;
  name_display: string;
  party: string | null;
  house: string | null;
  constituency: string | null;
  thumbnail_url: string | null;
  is_active: boolean;
  is_tracked: boolean;
}

export interface MemberSearchResponse {
  results: MemberSearchResult[];
  total: number;
}

export interface TrackedMemberSummary {
  parliament_id: number;
  name_display: string;
  party: string | null;
  house: string | null;
  constituency: string | null;
  thumbnail_url: string | null;
  is_active: boolean;
  last_refreshed_at: string | null;
  vote_count: number;
  question_count: number;
}

export interface TrackedMemberListResponse {
  members: TrackedMemberSummary[];
}

export interface MemberVoteRecord {
  division_id: number;
  parliament_division_id: number;
  title: string;
  date: string;
  vote: string;
  aye_count: number;
  no_count: number;
}

export interface MemberVotesResponse {
  parliament_id: number;
  votes: MemberVoteRecord[];
  total: number;
  has_more: boolean;
}

export interface MemberQuestionRecord {
  question_id: number;
  heading: string;
  date_tabled: string | null;
  date_answered: string | null;
  answering_body: string | null;
  question_text: string | null;
}

export interface MemberQuestionsResponse {
  parliament_id: number;
  questions: MemberQuestionRecord[];
  total: number;
  has_more: boolean;
}

export interface PartyBreakdown {
  party: string;
  abbreviation: string;
  colour: string;
  count: number;
}

export interface DivisionDetail {
  division_id: number;
  title: string;
  date: string;
  number: number | null;
  aye_count: number;
  no_count: number;
  is_deferred: boolean;
  friendly_description: string | null;
  friendly_title: string | null;
  aye_tellers: unknown;
  no_tellers: unknown;
  aye_party_breakdown: PartyBreakdown[];
  no_party_breakdown: PartyBreakdown[];
}
