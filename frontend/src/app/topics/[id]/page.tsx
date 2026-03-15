"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { ActorList } from "@/components/ActorList";
import { Timeline } from "@/components/Timeline";
import { useTimeline } from "@/hooks/useTimeline";
import { useRefreshTopic } from "@/hooks/useTopics";
import { api } from "@/lib/api";
import { RefreshTopicResponse } from "@/lib/types";

function formatQueryCount(value: number | undefined, label: string) {
  if (!value) {
    return null;
  }
  return `${value} ${label}`;
}

export default function TopicDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const topicId = Number.parseInt(params.id, 10);
  const refreshMutation = useRefreshTopic();

  const { data: topicData } = useQuery({
    queryKey: ["topic", topicId],
    queryFn: () =>
      api.getTopics().then((response) => response.topics.find((topic) => topic.id === topicId) ?? null),
    enabled: Number.isFinite(topicId),
  });

  const {
    data: timeline,
    isLoading: timelineLoading,
    error: timelineError,
  } = useTimeline(topicId, { limit: 100 });

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
              <span className="ml-2 text-sm font-normal text-slate-400">({timeline.total} events)</span>
            )}
          </h2>

          {timelineLoading && <div className="py-12 text-center text-slate-500">Loading timeline...</div>}
          {timelineError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              Failed to load timeline.
            </div>
          )}
          {timeline && <Timeline events={timeline.events} />}
        </div>

        <aside>
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Key Actors</h2>
          <ActorList actors={actorsData ?? []} />
        </aside>
      </div>
    </main>
  );
}
