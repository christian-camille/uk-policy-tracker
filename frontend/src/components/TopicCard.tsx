"use client";

import { formatDistanceToNow } from "date-fns";
import { ExternalLink, Pencil, RefreshCw, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useDeleteTopic, useRefreshTopic, useUpdateTopic } from "@/hooks/useTopics";
import { TopicSummary } from "@/lib/types";

export function TopicCard({ topic }: { topic: TopicSummary }) {
  const refreshMutation = useRefreshTopic();
  const deleteMutation = useDeleteTopic();
  const updateMutation = useUpdateTopic();
  const [isEditing, setIsEditing] = useState(false);
  const [labelDraft, setLabelDraft] = useState(topic.label);
  const [queriesDraft, setQueriesDraft] = useState(topic.search_queries.join(", "));
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    if (isEditing) {
      return;
    }

    setLabelDraft(topic.label);
    setQueriesDraft(topic.search_queries.join(", "));
    setEditError(null);
  }, [isEditing, topic.id, topic.label, topic.search_queries]);

  function startEditing() {
    setLabelDraft(topic.label);
    setQueriesDraft(topic.search_queries.join(", "));
    setEditError(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    setIsEditing(false);
  }

  function saveTopicEdits() {
    const nextLabel = labelDraft.trim();
    if (!nextLabel) {
      setEditError("Topic name cannot be empty.");
      return;
    }

    const nextQueries = queriesDraft
      .split(",")
      .map((query) => query.trim())
      .filter(Boolean);

    if (nextQueries.length === 0) {
      nextQueries.push(nextLabel);
    }

    setEditError(null);
    updateMutation.mutate(
      {
        topicId: topic.id,
        label: nextLabel,
        searchQueries: nextQueries,
      },
      {
        onSuccess: () => {
          setIsEditing(false);
        },
        onError: () => {
          setEditError("Failed to update topic. Please try again.");
        },
      }
    );
  }

  return (
    <div className="h-full rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {isEditing ? (
            <div className="space-y-3">
              <div>
                <label htmlFor={`topic-label-${topic.id}`} className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Topic name
                </label>
                <input
                  id={`topic-label-${topic.id}`}
                  type="text"
                  value={labelDraft}
                  onChange={(event) => setLabelDraft(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor={`topic-queries-${topic.id}`} className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Keywords (comma-separated)
                </label>
                <input
                  id={`topic-queries-${topic.id}`}
                  type="text"
                  value={queriesDraft}
                  onChange={(event) => setQueriesDraft(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none"
                />
              </div>

              {editError && <p className="text-sm text-red-700">{editError}</p>}

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={saveTopicEdits}
                  disabled={updateMutation.isPending}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? "Saving..." : "Save"}
                </button>
                <button
                  type="button"
                  onClick={cancelEditing}
                  disabled={updateMutation.isPending}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50 disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
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
            </>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <button
            onClick={() => {
              if (isEditing) {
                cancelEditing();
              } else {
                startEditing();
              }
            }}
            disabled={updateMutation.isPending}
            className="rounded-md p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
            title={isEditing ? "Cancel editing" : "Edit topic"}
          >
            {isEditing ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
          </button>
          <button
            onClick={() => refreshMutation.mutate(topic.id)}
            disabled={refreshMutation.isPending || isEditing || updateMutation.isPending}
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
            disabled={deleteMutation.isPending || isEditing || updateMutation.isPending}
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
