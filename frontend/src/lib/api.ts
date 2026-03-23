import {
  Actor,
  EntityDetail,
  RefreshAllTopicsResponse,
  RefreshTopicResponse,
  TimelineQueryParams,
  TimelineResponse,
  TopicSummary,
} from "./types";

const BFF_URL = "/api/bff";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export const api = {
  getTopics: (scope: "all" | "shared" | "private" = "all") => {
    const qs = new URLSearchParams();
    if (scope !== "all") {
      qs.set("scope", scope);
    }
    const query = qs.toString();
    return fetchApi<{ topics: TopicSummary[] }>(
      `${BFF_URL}/topics${query ? `?${query}` : ""}`
    );
  },

  createTopic: (
    label: string,
    payload: { searchQueries?: string[]; keywordGroups?: string[][]; excludedKeywords?: string[] }
  ) =>
    fetchApi<TopicSummary>(`${BFF_URL}/topics`, {
      method: "POST",
      body: JSON.stringify({
        label,
        search_queries: payload.searchQueries,
        keyword_groups: payload.keywordGroups,
        excluded_keywords: payload.excludedKeywords,
      }),
    }),

  updateTopic: (
    topicId: number,
    payload: { label?: string; searchQueries?: string[]; keywordGroups?: string[][]; excludedKeywords?: string[] }
  ) => {
    const body: {
      label?: string;
      search_queries?: string[];
      keyword_groups?: string[][];
      excluded_keywords?: string[];
    } = {};
    if (payload.label !== undefined) {
      body.label = payload.label;
    }
    if (payload.searchQueries !== undefined) {
      body.search_queries = payload.searchQueries;
    }
    if (payload.keywordGroups !== undefined) {
      body.keyword_groups = payload.keywordGroups;
    }
    if (payload.excludedKeywords !== undefined) {
      body.excluded_keywords = payload.excludedKeywords;
    }

    return fetchApi<TopicSummary>(`${BFF_URL}/topics/${topicId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  deleteTopic: (topicId: number) =>
    fetchApi<void>(`${BFF_URL}/topics/${topicId}`, { method: "DELETE" }),

  getTimeline: (
    topicId: number,
    params?: TimelineQueryParams
  ) => {
    const qs = new URLSearchParams();
    if (params?.since) qs.set("since", params.since);
    if (params?.until) qs.set("until", params.until);
    params?.eventTypes?.forEach((value) => qs.append("event_type", value));
    params?.sourceEntityTypes?.forEach((value) => qs.append("source_entity_type", value));
    if (params?.q?.trim()) qs.set("q", params.q.trim());
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString();
    return fetchApi<TimelineResponse>(
      `${BFF_URL}/topics/${topicId}/timeline${query ? `?${query}` : ""}`
    );
  },

  getEntity: (nodeId: number) => fetchApi<EntityDetail>(`${BFF_URL}/entities/${nodeId}`),

  getEntityBySource: (entityType: string, entityId: number) =>
    fetchApi<EntityDetail>(
      `${BFF_URL}/entities/by-source/${encodeURIComponent(entityType)}/${entityId}`
    ),

  getActors: (topicId: number) =>
    fetchApi<Actor[]>(`${BFF_URL}/topics/${topicId}/actors`),

  refreshTopic: (topicId: number) =>
    fetchApi<RefreshTopicResponse>(`${BFF_URL}/topics/${topicId}/refresh`, {
      method: "POST",
    }),

  refreshAllTopics: () =>
    fetchApi<RefreshAllTopicsResponse>(`${BFF_URL}/topics/refresh-all`, {
      method: "POST",
    }),
};
