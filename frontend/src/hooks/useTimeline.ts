"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useTimeline(
  topicId: number,
  params?: { since?: string; limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: ["timeline", topicId, params],
    queryFn: () => api.getTimeline(topicId, params),
    enabled: !!topicId,
  });
}
