"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TimelineQueryParams } from "@/lib/types";

export function useTimeline(
  topicId: number | undefined,
  params?: TimelineQueryParams
) {
  const eventTypesKey = params?.eventTypes ? [...params.eventTypes].sort().join(",") : null;
  const sourceTypesKey = params?.sourceEntityTypes ? [...params.sourceEntityTypes].sort().join(",") : null;

  return useQuery({
    queryKey: [
      "timeline",
      topicId ?? null,
      params?.since ?? null,
      params?.until ?? null,
      eventTypesKey,
      sourceTypesKey,
      params?.q ?? null,
      params?.limit ?? null,
      params?.offset ?? null,
    ],
    queryFn: () => {
      if (topicId === undefined) {
        throw new Error("Missing topic id");
      }

      return api.getTimeline(topicId, params);
    },
    placeholderData: (previousData) => previousData,
    enabled: typeof topicId === "number",
  });
}
