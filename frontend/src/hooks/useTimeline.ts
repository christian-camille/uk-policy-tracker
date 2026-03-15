"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useTimeline(
  topicId: number,
  params?: { since?: string; limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: ["timeline", topicId, params?.since ?? null, params?.limit ?? null, params?.offset ?? null],
    queryFn: () => api.getTimeline(topicId, params),
    enabled: Number.isFinite(topicId),
  });
}
