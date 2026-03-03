"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { RefreshCw, Trash2, ExternalLink } from "lucide-react";
import { TopicSummary } from "@/lib/types";
import { useRefreshTopic, useDeleteTopic } from "@/hooks/useTopics";

export function TopicCard({ topic }: { topic: TopicSummary }) {
  const refreshMutation = useRefreshTopic();
  const deleteMutation = useDeleteTopic();

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <Link
            href={`/topics/${topic.id}`}
            className="text-lg font-semibold text-gray-900 hover:text-blue-700 flex items-center gap-1.5"
          >
            {topic.label}
            <ExternalLink className="w-4 h-4 text-gray-400" />
          </Link>

          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-500">
            {topic.last_refreshed_at ? (
              <span>
                Updated{" "}
                {formatDistanceToNow(new Date(topic.last_refreshed_at), {
                  addSuffix: true,
                })}
              </span>
            ) : (
              <span>Never refreshed</span>
            )}

            {topic.new_items_count > 0 && (
              <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                {topic.new_items_count} items
              </span>
            )}
          </div>

          <div className="mt-2 flex flex-wrap gap-1.5">
            {topic.search_queries?.map((q) => (
              <span
                key={q}
                className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
              >
                {q}
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => refreshMutation.mutate(topic.id)}
            disabled={refreshMutation.isPending}
            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50"
            title="Refresh topic data"
          >
            <RefreshCw
              className={`w-4 h-4 ${refreshMutation.isPending ? "animate-spin" : ""}`}
            />
          </button>
          <button
            onClick={() => {
              if (confirm(`Remove "${topic.label}" from your watchlist?`)) {
                deleteMutation.mutate(topic.id);
              }
            }}
            disabled={deleteMutation.isPending}
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50"
            title="Remove topic"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
