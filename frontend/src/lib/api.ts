import { TopicSummary, TimelineResponse, EntityDetail } from "./types";

const BASE_URL = "/api";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  getTopics: () => fetchApi<{ topics: TopicSummary[] }>("/topics"),

  createTopic: (label: string, searchQueries: string[]) =>
    fetchApi<TopicSummary>("/topics", {
      method: "POST",
      body: JSON.stringify({ label, search_queries: searchQueries }),
    }),

  deleteTopic: (topicId: number) =>
    fetchApi<void>(`/topics/${topicId}`, { method: "DELETE" }),

  getTimeline: (
    topicId: number,
    params?: { since?: string; limit?: number; offset?: number }
  ) => {
    const qs = new URLSearchParams();
    if (params?.since) qs.set("since", params.since);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString();
    return fetchApi<TimelineResponse>(
      `/topics/${topicId}/timeline${query ? `?${query}` : ""}`
    );
  },

  getEntity: (nodeId: number) =>
    fetchApi<EntityDetail>(`/entities/${nodeId}`),

  refreshTopic: (topicId: number) =>
    fetchApi<{ status: string }>(`/topics/${topicId}/refresh`, {
      method: "POST",
    }),
};
