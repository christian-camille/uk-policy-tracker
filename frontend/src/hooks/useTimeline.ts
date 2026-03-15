"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TimelineQueryParams } from "@/lib/types";

export function useTimeline(
  topicId: number,
  params?: TimelineQueryParams
) {
  const pageSize = params?.limit ?? 50;
  const eventTypesKey = params?.eventTypes ? [...params.eventTypes].sort().join(",") : null;
  const sourceTypesKey = params?.sourceEntityTypes ? [...params.sourceEntityTypes].sort().join(",") : null;

  return useInfiniteQuery({
    queryKey: [
      "timeline",
      topicId,
      params?.since ?? null,
      params?.until ?? null,
      eventTypesKey,
      sourceTypesKey,
      params?.q ?? null,
      pageSize,
    ],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      api.getTimeline(topicId, {
        ...params,
        limit: pageSize,
        offset: pageParam,
      }),
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.has_more) {
        return undefined;
      }

      return allPages.reduce((count, page) => count + page.events.length, 0);
    },
    enabled: Number.isFinite(topicId),
  });
}
