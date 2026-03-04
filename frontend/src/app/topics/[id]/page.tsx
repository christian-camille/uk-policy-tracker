"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { Timeline } from "@/components/Timeline";
import { ActorList } from "@/components/ActorList";
import { useTimeline } from "@/hooks/useTimeline";
import { useRefreshTopic } from "@/hooks/useTopics";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function TopicDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const topicId = parseInt(id, 10);
  const refreshMutation = useRefreshTopic();

  const { data: topicData } = useQuery({
    queryKey: ["topic", topicId],
    queryFn: () =>
      api
        .getTopics()
        .then((res) => res.topics.find((t) => t.id === topicId) ?? null),
    enabled: !!topicId,
  });

  const {
    data: timeline,
    isLoading: timelineLoading,
    error: timelineError,
  } = useTimeline(topicId, { limit: 100 });

  const { data: actorsData } = useQuery({
    queryKey: ["actors", topicId],
    queryFn: () => api.getActors(topicId),
    enabled: !!topicId,
  });

  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Watchlist
        </Link>

        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            {topicData?.label ?? `Topic #${topicId}`}
          </h1>
          <button
            onClick={() => refreshMutation.mutate(topicId)}
            disabled={refreshMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw
              className={`w-4 h-4 ${refreshMutation.isPending ? "animate-spin" : ""}`}
            />
            {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
          </button>
        </div>

        {topicData?.search_queries && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {topicData.search_queries.map((q: string) => (
              <span
                key={q}
                className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
              >
                {q}
              </span>
            ))}
          </div>
        )}

        {refreshMutation.isSuccess && (
          <div className="mt-3 bg-green-50 border border-green-200 rounded-md p-3 text-sm text-green-800">
            Refresh queued. Data will update shortly.
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Timeline
            {timeline && (
              <span className="text-sm font-normal text-gray-400 ml-2">
                ({timeline.total} events)
              </span>
            )}
          </h2>

          {timelineLoading && (
            <div className="text-center py-12 text-gray-500">
              Loading timeline...
            </div>
          )}
          {timelineError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
              Failed to load timeline.
            </div>
          )}
          {timeline && <Timeline events={timeline.events} />}
        </div>

        <aside>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Key Actors
          </h2>
          <ActorList actors={actorsData ?? []} />
        </aside>
      </div>
    </main>
  );
}
