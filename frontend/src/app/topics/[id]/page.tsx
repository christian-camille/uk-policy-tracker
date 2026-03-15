"use client";

import { useQuery } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import type { ReadonlyURLSearchParams } from "next/navigation";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { ActorList } from "@/components/ActorList";
import { Timeline } from "@/components/Timeline";
import { TimelineFilters } from "@/components/TimelineFilters";
import { useTimeline } from "@/hooks/useTimeline";
import { useRefreshTopic } from "@/hooks/useTopics";
import { api } from "@/lib/api";
import { TIMELINE_EVENT_OPTIONS, TIMELINE_SOURCE_OPTIONS } from "@/lib/timeline";
import {
  RefreshTopicResponse,
  TimelineEventType,
  TimelineQueryParams,
  TimelineSourceType,
} from "@/lib/types";

function formatQueryCount(value: number | undefined, label: string) {
  if (!value) {
    return null;
  }
  return `${value} ${label}`;
}

const TIMELINE_EVENT_TYPE_VALUES = new Set<TimelineEventType>(
  TIMELINE_EVENT_OPTIONS.map((option) => option.value)
);
const TIMELINE_SOURCE_TYPE_VALUES = new Set<TimelineSourceType>(
  TIMELINE_SOURCE_OPTIONS.map((option) => option.value)
);

function normalizeDateValue(value: string | null): string {
  if (!value) {
    return "";
  }

  return value.includes("T") ? value.slice(0, 10) : value;
}

function getMultiValue<T extends string>(
  searchParams: ReadonlyURLSearchParams,
  key: string,
  allowedValues: Set<T>
): T[] {
  return searchParams.getAll(key).filter((value: string): value is T => allowedValues.has(value as T));
}

function getPresetRange(days: number) {
  const today = new Date();

  return {
    since: format(subDays(today, days - 1), "yyyy-MM-dd"),
    until: format(today, "yyyy-MM-dd"),
  };
}

function getActivePresetDays(since: string, until: string): number | null {
  if (!since || !until) {
    return null;
  }

  for (const days of [7, 30, 90]) {
    const preset = getPresetRange(days);
    if (preset.since === since && preset.until === until) {
      return days;
    }
  }

  return null;
}

export default function TopicDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isRoutePending, startRouteTransition] = useTransition();
  const topicId = Number.parseInt(params.id, 10);
  const refreshMutation = useRefreshTopic();

  const since = normalizeDateValue(searchParams.get("since"));
  const until = normalizeDateValue(searchParams.get("until"));
  const query = searchParams.get("q") ?? "";
  const selectedEventTypes = getMultiValue(searchParams, "event_type", TIMELINE_EVENT_TYPE_VALUES);
  const selectedSourceTypes = getMultiValue(
    searchParams,
    "source_entity_type",
    TIMELINE_SOURCE_TYPE_VALUES
  );
  const answeredOnly = searchParams.get("answered") === "1";
  const [queryDraft, setQueryDraft] = useState(query);
  const activePresetDays = getActivePresetDays(since, until);
  const effectiveEventTypes = answeredOnly ? (["question_answered"] as TimelineEventType[]) : selectedEventTypes;
  const hasActiveFilters =
    Boolean(since) ||
    Boolean(until) ||
    Boolean(query.trim()) ||
    answeredOnly ||
    selectedEventTypes.length > 0 ||
    selectedSourceTypes.length > 0;

  const timelineParams: TimelineQueryParams = {
    limit: 100,
  };

  if (since) {
    timelineParams.since = since;
  }
  if (until) {
    timelineParams.until = until;
  }
  if (effectiveEventTypes.length > 0) {
    timelineParams.eventTypes = effectiveEventTypes;
  }
  if (selectedSourceTypes.length > 0) {
    timelineParams.sourceEntityTypes = selectedSourceTypes;
  }
  if (query.trim()) {
    timelineParams.q = query;
  }

  function replaceSearchParams(mutator: (nextParams: URLSearchParams) => void) {
    const nextParams = new URLSearchParams(searchParams.toString());
    mutator(nextParams);
    const nextQuery = nextParams.toString();

    startRouteTransition(() => {
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    });
  }

  function setSingleFilter(key: string, value: string) {
    replaceSearchParams((nextParams) => {
      if (value) {
        nextParams.set(key, value);
      } else {
        nextParams.delete(key);
      }
      nextParams.delete("offset");
    });
  }

  function setMultiFilter(key: string, values: string[]) {
    replaceSearchParams((nextParams) => {
      nextParams.delete(key);
      values.forEach((value) => nextParams.append(key, value));
      nextParams.delete("offset");
    });
  }

  function toggleEventType(value: TimelineEventType) {
    const nextValues = selectedEventTypes.includes(value)
      ? selectedEventTypes.filter((eventType) => eventType !== value)
      : [...selectedEventTypes, value];

    replaceSearchParams((nextParams) => {
      nextParams.delete("answered");
      nextParams.delete("event_type");
      nextValues.forEach((eventType) => nextParams.append("event_type", eventType));
      nextParams.delete("offset");
    });
  }

  function toggleSourceType(value: TimelineSourceType) {
    const nextValues = selectedSourceTypes.includes(value)
      ? selectedSourceTypes.filter((sourceType) => sourceType !== value)
      : [...selectedSourceTypes, value];

    setMultiFilter("source_entity_type", nextValues);
  }

  function setAnsweredOnly(value: boolean) {
    replaceSearchParams((nextParams) => {
      nextParams.delete("event_type");
      nextParams.delete("offset");
      if (value) {
        nextParams.set("answered", "1");
      } else {
        nextParams.delete("answered");
      }
    });
  }

  function applyPreset(days: number) {
    const preset = getPresetRange(days);

    replaceSearchParams((nextParams) => {
      nextParams.set("since", preset.since);
      nextParams.set("until", preset.until);
      nextParams.delete("offset");
    });
  }

  function clearFilters() {
    replaceSearchParams((nextParams) => {
      ["since", "until", "q", "event_type", "source_entity_type", "answered", "offset"].forEach((key) => {
        nextParams.delete(key);
      });
    });
  }

  useEffect(() => {
    setQueryDraft(query);
  }, [query]);

  useEffect(() => {
    if (queryDraft === query) {
      return;
    }

    const handle = window.setTimeout(() => {
      const nextParams = new URLSearchParams(searchParams.toString());
      const nextQueryValue = queryDraft.trim();

      if (nextQueryValue) {
        nextParams.set("q", nextQueryValue);
      } else {
        nextParams.delete("q");
      }
      nextParams.delete("offset");

      const nextQuery = nextParams.toString();
      startRouteTransition(() => {
        router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
      });
    }, 350);

    return () => window.clearTimeout(handle);
  }, [pathname, query, queryDraft, router, searchParams, startRouteTransition]);

  const { data: topicData } = useQuery({
    queryKey: ["topic", topicId],
    queryFn: () =>
      api.getTopics().then((response) => response.topics.find((topic) => topic.id === topicId) ?? null),
    enabled: Number.isFinite(topicId),
  });

  const {
    data: timeline,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
    isLoading: timelineLoading,
    error: timelineError,
  } = useTimeline(topicId, timelineParams);

  const timelinePages = timeline?.pages ?? [];
  const timelineEvents = timelinePages.flatMap((page) => page.events);
  const timelineTotal = timelinePages[0]?.total ?? 0;
  const loadedTimelineCount = timelineEvents.length;

  const { data: actorsData } = useQuery({
    queryKey: ["actors", topicId],
    queryFn: () => api.getActors(topicId),
    enabled: Number.isFinite(topicId),
  });

  const refreshResult = refreshMutation.data as RefreshTopicResponse | undefined;
  const summaryItems = [
    formatQueryCount(refreshResult?.result.govuk.items_ingested, "GOV.UK docs"),
    formatQueryCount(refreshResult?.result.parliament.bills, "bills"),
    formatQueryCount(refreshResult?.result.parliament.questions, "questions"),
    formatQueryCount(refreshResult?.result.parliament.divisions, "divisions"),
    formatQueryCount(refreshResult?.result.events.events_created, "events"),
    formatQueryCount(refreshResult?.result.mentions.mentions_created, "mentions"),
  ].filter(Boolean);

  return (
    <main className="mx-auto max-w-6xl p-6">
      <div className="mb-6">
        <Link
          href="/"
          className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Watchlist
        </Link>

        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
              {topicData?.label ?? `Topic #${topicId}`}
            </h1>
            {topicData?.search_queries && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {topicData.search_queries.map((query) => (
                  <span
                    key={query}
                    className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600"
                  >
                    {query}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => refreshMutation.mutate(topicId)}
            disabled={refreshMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
            {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
          </button>
        </div>

        {refreshMutation.isPending && (
          <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
            Fetching GOV.UK and Parliament updates, creating events, matching entities, and rebuilding the graph.
          </div>
        )}

        {refreshMutation.isError && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            Refresh failed. Try again after the upstream APIs recover.
          </div>
        )}

        {refreshMutation.isSuccess && refreshResult && (
          <div className="mt-4 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-900">
            <p className="font-medium">Refresh completed.</p>
            <p className="mt-1">
              {summaryItems.length > 0 ? summaryItems.join(", ") : "No new items were found."}
            </p>
            <p className="mt-1 text-green-800">
              Graph rebuilt with {refreshResult.result.graph.nodes} nodes and {refreshResult.result.graph.edges} edges.
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Timeline
            {timeline && (
              <span className="ml-2 text-sm font-normal text-slate-400">
                ({timelineTotal} {hasActiveFilters ? "matching" : "total"} event{timelineTotal === 1 ? "" : "s"})
              </span>
            )}
          </h2>

          <TimelineFilters
            since={since}
            until={until}
            query={queryDraft}
            eventTypes={selectedEventTypes}
            sourceEntityTypes={selectedSourceTypes}
            answeredOnly={answeredOnly}
            activePresetDays={activePresetDays}
            hasActiveFilters={hasActiveFilters}
            resultCount={timeline ? timelineTotal : undefined}
            isPending={isRoutePending || (isFetching && !isFetchingNextPage)}
            onSinceChange={(value) => setSingleFilter("since", value)}
            onUntilChange={(value) => setSingleFilter("until", value)}
            onQueryChange={setQueryDraft}
            onEventTypeToggle={toggleEventType}
            onSourceTypeToggle={toggleSourceType}
            onAnsweredOnlyChange={setAnsweredOnly}
            onPresetSelect={applyPreset}
            onClear={clearFilters}
          />

          {timelineLoading && <div className="py-12 text-center text-slate-500">Loading timeline...</div>}
          {timelineError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              Failed to load timeline.
            </div>
          )}
          {timeline && (
            <>
              <Timeline
                events={timelineEvents}
                emptyMessage={
                  hasActiveFilters
                    ? "No events match the current filters. Clear or adjust them to broaden the timeline."
                    : undefined
                }
              />

              {loadedTimelineCount > 0 && hasNextPage && (
                <div className="mt-4 flex flex-col items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void fetchNextPage()}
                    disabled={isFetchingNextPage}
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isFetchingNextPage ? "Loading more..." : "Load more events"}
                  </button>
                  <p className="text-xs text-slate-500">
                    Showing {loadedTimelineCount} of {timelineTotal} events
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        <aside>
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Key Actors</h2>
          <ActorList actors={actorsData ?? []} />
        </aside>
      </div>
    </main>
  );
}
