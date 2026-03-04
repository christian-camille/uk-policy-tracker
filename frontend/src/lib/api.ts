import { TopicSummary, TimelineResponse, EntityDetail } from "./types";

const BFF_URL = "/api/bff";
const AUTH_URL = "/api/auth";

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

  createTopic: (label: string, searchQueries: string[], isGlobal: boolean) =>
    fetchApi<TopicSummary>(`${BFF_URL}/topics`, {
      method: "POST",
      body: JSON.stringify({
        label,
        search_queries: searchQueries,
        is_global: isGlobal,
      }),
    }),

  deleteTopic: (topicId: number) =>
    fetchApi<void>(`${BFF_URL}/topics/${topicId}`, { method: "DELETE" }),

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
      `${BFF_URL}/topics/${topicId}/timeline${query ? `?${query}` : ""}`
    );
  },

  getEntity: (nodeId: number) => fetchApi<EntityDetail>(`${BFF_URL}/entities/${nodeId}`),

  getActors: (topicId: number) => fetchApi(`${BFF_URL}/topics/${topicId}/actors`),

  refreshTopic: (topicId: number) =>
    fetchApi<{ status: string }>(`${BFF_URL}/topics/${topicId}/refresh`, {
      method: "POST",
    }),

  getCurrentUser: async () => {
    const res = await fetch(`${AUTH_URL}/me`, { credentials: "include" });
    if (res.status === 401) {
      return { user: null };
    }
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<{ user: { id: string; email: string | null } | null }>;
  },


  logout: () => fetchApi<{ status: string }>(`${AUTH_URL}/logout`, { method: "POST" }),

  loginWithPassword: (email: string, password: string) =>
    fetchApi<{ status: string }>(`${AUTH_URL}/login`, {
      method: "POST",
      body: JSON.stringify({ type: "password", email, password }),
    }),

  loginWithMagicLink: (email: string) =>
    fetchApi<{ status: string }>(`${AUTH_URL}/login`, {
      method: "POST",
      body: JSON.stringify({ type: "magic_link", email }),
    }),

  loginWithOAuth: (provider: "google" | "azure") =>
    fetchApi<{ url: string }>(`${AUTH_URL}/login`, {
      method: "POST",
      body: JSON.stringify({ type: "oauth", provider }),
    }),
};
