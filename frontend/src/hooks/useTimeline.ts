"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TimelineQueryParams } from "@/lib/types";

export function useTimeline(
  topicId: number,
  params?: TimelineQueryParams
) {
  const eventTypesKey = params?.eventTypes ? [...params.eventTypes].sort().join(",") : null;
  const sourceTypesKey = params?.sourceEntityTypes ? [...params.sourceEntityTypes].sort().join(",") : null;

  return useQuery({
    queryKey: [
      "timeline",
      topicId,
      params?.since ?? null,
      params?.until ?? null,
      eventTypesKey,
      sourceTypesKey,
      params?.q ?? null,
      params?.limit ?? null,
      params?.offset ?? null,
    ],
    queryFn: () => api.getTimeline(topicId, params),
    placeholderData: (previousData) => previousData,
    enabled: Number.isFinite(topicId),
  });
}
