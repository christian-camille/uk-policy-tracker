"use client";

import { useQuery } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import type { ReadonlyURLSearchParams } from "next/navigation";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useTransition } from "react";
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

const DEFAULT_TIMELINE_PAGE_SIZE = 25;
const ALLOWED_TIMELINE_PAGE_SIZES = [25, 50, 100] as const;

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

function normalizePageValue(value: string | null): number {
  if (!value) {
    return 1;
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return 1;
  }

  return parsed;
}

function normalizePageSizeValue(value: string | null): number {
  if (!value) {
    return DEFAULT_TIMELINE_PAGE_SIZE;
  }

  const parsed = Number.parseInt(value, 10);
  if (!ALLOWED_TIMELINE_PAGE_SIZES.includes(parsed as (typeof ALLOWED_TIMELINE_PAGE_SIZES)[number])) {
    return DEFAULT_TIMELINE_PAGE_SIZE;
  }

  return parsed;
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

function buildPaginationItems(currentPage: number, totalPages: number): Array<number | string> {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  if (currentPage <= 3) {
    return [1, 2, 3, 4, "ellipsis-start", totalPages];
  }

  if (currentPage >= totalPages - 2) {
    return [1, "ellipsis-end", totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  return [
    1,
    "ellipsis-left",
    currentPage - 1,
    currentPage,
    currentPage + 1,
    "ellipsis-right",
    totalPages,
  ];
}

export default function TopicDetailPage() {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isRoutePending, startRouteTransition] = useTransition();
  const parsedTopicId = Number.parseInt(params.id ?? "", 10);
  const topicId = Number.isFinite(parsedTopicId) ? parsedTopicId : undefined;
  const refreshMutation = useRefreshTopic();

  const since = normalizeDateValue(searchParams.get("since"));
  const until = normalizeDateValue(searchParams.get("until"));
  const query = searchParams.get("q") ?? "";
  const currentPage = normalizePageValue(searchParams.get("page"));
  const pageSize = normalizePageSizeValue(searchParams.get("pageSize"));
  const selectedEventTypes = getMultiValue(searchParams, "event_type", TIMELINE_EVENT_TYPE_VALUES);
  const selectedSourceTypes = getMultiValue(
    searchParams,
    "source_entity_type",
    TIMELINE_SOURCE_TYPE_VALUES
  );
  const answeredOnly = searchParams.get("answered") === "1";
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
    limit: pageSize,
    offset: (currentPage - 1) * pageSize,
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

  function replaceSearchParams(
    mutator: (nextParams: URLSearchParams) => void,
    options?: { scrollToTop?: boolean }
  ) {
    const nextParams = new URLSearchParams(searchParams.toString());
    mutator(nextParams);
    const nextQuery = nextParams.toString();

    startRouteTransition(() => {
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, {
        scroll: options?.scrollToTop ?? false,
      });
      if (options?.scrollToTop) {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
  }

  function setSingleFilter(key: string, value: string) {
    replaceSearchParams((nextParams) => {
      if (value) {
        nextParams.set(key, value);
      } else {
        nextParams.delete(key);
      }
      nextParams.delete("page");
    });
  }

  function setMultiFilter(key: string, values: string[]) {
    replaceSearchParams((nextParams) => {
      nextParams.delete(key);
      values.forEach((value) => nextParams.append(key, value));
      nextParams.delete("page");
    });
  }

  function setPage(page: number) {
    const normalizedPage = totalPages > 0 ? Math.min(Math.max(page, 1), totalPages) : Math.max(page, 1);

    replaceSearchParams((nextParams) => {
      if (normalizedPage <= 1) {
        nextParams.delete("page");
      } else {
        nextParams.set("page", String(normalizedPage));
      }
    }, { scrollToTop: true });
  }

  function setPageSize(nextPageSize: number) {
    replaceSearchParams((nextParams) => {
      nextParams.set("pageSize", String(nextPageSize));
      nextParams.delete("page");
    }, { scrollToTop: true });
  }

  function handlePageJump(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const rawPageValue = formData.get("page");
    const submittedValue = typeof rawPageValue === "string" ? rawPageValue : "";

    if (!submittedValue) {
      return;
    }

    const parsedPage = Number.parseInt(submittedValue, 10);
    if (!Number.isFinite(parsedPage)) {
      return;
    }

    setPage(parsedPage);
  }

  function setQuery(value: string) {
    const nextQueryValue = value.trim();

    replaceSearchParams((nextParams) => {
      if (nextQueryValue) {
        nextParams.set("q", nextQueryValue);
      } else {
        nextParams.delete("q");
      }
      nextParams.delete("page");
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
      nextParams.delete("page");
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
      nextParams.delete("page");
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
      nextParams.delete("page");
    });
  }

  function clearFilters() {
    replaceSearchParams((nextParams) => {
      ["since", "until", "q", "event_type", "source_entity_type", "answered", "page"].forEach((key) => {
        nextParams.delete(key);
      });
    });
  }

  const { data: topicData } = useQuery({
    queryKey: ["topic", topicId ?? null],
    queryFn: () =>
      api.getTopics().then((response) => response.topics.find((topic) => topic.id === topicId) ?? null),
    enabled: typeof topicId === "number",
  });

  const {
    data: timeline,
    isFetching,
    isLoading: timelineLoading,
    error: timelineError,
  } = useTimeline(topicId, timelineParams);
  const timelineEvents = timeline?.events ?? [];
  const timelineTotal = timeline?.total ?? 0;
  const totalPages = timelineTotal > 0 ? Math.ceil(timelineTotal / pageSize) : 0;
  const paginationItems = totalPages > 1 ? buildPaginationItems(currentPage, totalPages) : [];

  useEffect(() => {
    if (totalPages > 0 && currentPage > totalPages) {
      setPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const { data: actorsData } = useQuery({
    queryKey: ["actors", topicId ?? null],
    queryFn: () => {
      if (topicId === undefined) {
        throw new Error("Missing topic id");
      }

      return api.getActors(topicId);
    },
    enabled: typeof topicId === "number",
  });
  const actorCount = actorsData?.length ?? 0;

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
    <main>
      {/* Gradient page header */}
      <div className="border-b border-slate-200/60 bg-gradient-to-b from-slate-100 via-slate-50/80 to-transparent pb-6 pt-6">
        <div className="mx-auto max-w-6xl px-6">
          <Link
            href="/"
            className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-400 transition-colors hover:text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Watchlist
          </Link>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                {topicData?.label ?? (topicId !== undefined ? `Topic #${topicId}` : "Topic")}
              </h1>
              {topicData?.keyword_groups && (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {topicData.keyword_groups[0]?.map((keyword) => (
                    <span
                      key={`kw-${keyword}`}
                      className="rounded-md bg-white/80 px-2 py-0.5 text-xs text-slate-500 ring-1 ring-slate-200"
                    >
                      {keyword}
                    </span>
                  ))}
                  {(topicData.keyword_groups.length > 1 || topicData.excluded_keywords.length > 0) && (
                    <span className="text-xs text-slate-400">
                      +{topicData.keyword_groups.slice(1).flat().length + topicData.excluded_keywords.length} more
                    </span>
                  )}
                </div>
              )}
            </div>
            <button
              onClick={() => {
                if (topicId !== undefined) {
                  refreshMutation.mutate(topicId);
                }
              }}
              disabled={refreshMutation.isPending || topicId === undefined}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
              {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
            </button>
          </div>
        </div>
      </div>

      {/* Content area */}
      <div className="mx-auto max-w-6xl px-6 py-6">
        {/* Status banners */}
        {refreshMutation.isPending && (
          <div className="mb-5 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-900">
            Fetching GOV.UK and Parliament updates, creating events, matching entities, and rebuilding the graph.
          </div>
        )}

        {refreshMutation.isError && (
          <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            Refresh failed. Try again after the upstream APIs recover.
          </div>
        )}

        {refreshMutation.isSuccess && refreshResult && (
          <div className="mb-5 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-900">
            <p className="font-medium">Refresh completed.</p>
            <p className="mt-1">
              {summaryItems.length > 0 ? summaryItems.join(", ") : "No new items were found."}
            </p>
            <p className="mt-1 text-green-800">
              Graph rebuilt with {refreshResult.result.graph.nodes} nodes and {refreshResult.result.graph.edges} edges.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="mb-4 flex items-center gap-3">
              <h2 className="text-lg font-semibold text-slate-900">Timeline</h2>
              {timeline && (
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
                  {timelineTotal} {hasActiveFilters ? "matching" : "total"}
                </span>
              )}
            </div>

            <TimelineFilters
              since={since}
              until={until}
              query={query}
              eventTypes={selectedEventTypes}
              sourceEntityTypes={selectedSourceTypes}
              answeredOnly={answeredOnly}
              activePresetDays={activePresetDays}
              hasActiveFilters={hasActiveFilters}
              resultCount={timeline ? timelineTotal : undefined}
              isPending={isRoutePending || (isFetching && !timelineLoading)}
              onSinceChange={(value) => setSingleFilter("since", value)}
              onUntilChange={(value) => setSingleFilter("until", value)}
              onQueryChange={setQuery}
              onEventTypeToggle={toggleEventType}
              onSourceTypeToggle={toggleSourceType}
              onAnsweredOnlyChange={setAnsweredOnly}
              onPresetSelect={applyPreset}
              onClear={clearFilters}
            />

            {timelineLoading && <div className="py-12 text-center text-slate-500">Loading timeline...</div>}
            {timelineError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
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

                {timelineTotal > 0 && totalPages > 1 && (
                  <div className="mt-5 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-sm text-slate-500">
                        Page {currentPage} of {totalPages}
                        <span className="mx-2 text-slate-300">|</span>
                        Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, timelineTotal)} of {timelineTotal}
                      </p>

                      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                        <button
                          type="button"
                          onClick={() => setPage(currentPage - 1)}
                          disabled={currentPage === 1}
                          className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Previous
                        </button>

                        {paginationItems.map((item) =>
                          typeof item === "number" ? (
                            <button
                              key={item}
                              type="button"
                              onClick={() => setPage(item)}
                              aria-current={item === currentPage ? "page" : undefined}
                              className={`shrink-0 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                                item === currentPage
                                  ? "border-indigo-600 bg-indigo-600 text-white"
                                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                              }`}
                            >
                              {item}
                            </button>
                          ) : (
                            <span key={item} className="px-1 text-sm text-slate-400">
                              ...
                            </span>
                          )
                        )}

                        <button
                          type="button"
                          onClick={() => setPage(currentPage + 1)}
                          disabled={currentPage >= totalPages}
                          className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Next
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 pt-3 text-sm text-slate-600">
                      <label htmlFor="timeline-page-size" className="flex items-center gap-2">
                        <span className="font-medium text-slate-600">Per page</span>
                        <select
                          id="timeline-page-size"
                          value={pageSize}
                          onChange={(event) => setPageSize(Number.parseInt(event.target.value, 10))}
                          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-indigo-400 focus:outline-none"
                        >
                          {ALLOWED_TIMELINE_PAGE_SIZES.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      </label>

                      <form onSubmit={handlePageJump} className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
                        <label htmlFor="timeline-page-jump" className="font-medium text-slate-600">
                          Jump to page
                        </label>
                        <input
                          id="timeline-page-jump"
                          name="page"
                          key={currentPage}
                          type="number"
                          inputMode="numeric"
                          min={1}
                          max={totalPages}
                          defaultValue={currentPage}
                          className="w-20 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-indigo-400 focus:outline-none"
                        />
                        <button
                          type="submit"
                          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
                        >
                          Go
                        </button>
                      </form>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <aside>
            <div className="mb-4 flex items-center gap-3">
              <h2 className="text-lg font-semibold text-slate-900">Key Actors</h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
                {actorCount}
              </span>
            </div>
            <ActorList actors={actorsData ?? []} />
          </aside>
        </div>
      </div>
    </main>
  );
}
