"use client";

import { formatDistanceToNow } from "date-fns";
import { ExternalLink, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useDeleteTopic, useRefreshTopic } from "@/hooks/useTopics";
import { TopicSummary } from "@/lib/types";

export function TopicCard({ topic }: { topic: TopicSummary }) {
  const refreshMutation = useRefreshTopic();
  const deleteMutation = useDeleteTopic();

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <Link
            href={`/topics/${topic.id}`}
            className="inline-flex items-center gap-1.5 text-lg font-semibold text-slate-900 hover:text-blue-700"
          >
            {topic.label}
            <ExternalLink className="h-4 w-4 text-slate-400" />
          </Link>

          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-500">
            {topic.last_refreshed_at ? (
              <span>
                Updated {formatDistanceToNow(new Date(topic.last_refreshed_at), { addSuffix: true })}
              </span>
            ) : (
              <span>Never refreshed</span>
            )}
            {topic.new_items_count > 0 && (
              <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                {topic.new_items_count} items
              </span>
            )}
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {topic.search_queries.map((query) => (
              <span
                key={query}
                className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600"
              >
                {query}
              </span>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <button
            onClick={() => refreshMutation.mutate(topic.id)}
            disabled={refreshMutation.isPending}
            className="rounded-md p-2 text-slate-400 transition-colors hover:bg-blue-50 hover:text-blue-600 disabled:opacity-50"
            title="Refresh topic data"
          >
            <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => {
              if (confirm(`Remove "${topic.label}" from your watchlist?`)) {
                deleteMutation.mutate(topic.id);
              }
            }}
            disabled={deleteMutation.isPending}
            className="rounded-md p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
            title="Remove topic"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
