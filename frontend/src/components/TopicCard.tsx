"use client";

import { formatDistanceToNow } from "date-fns";
import { ExternalLink, Pencil, RefreshCw, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useDeleteTopic, useRefreshTopic, useUpdateTopic } from "@/hooks/useTopics";
import { buildInitialGroupDrafts, ensureKeywordGroups, formatKeywordList, parseKeywordList } from "@/lib/topicRules";
import { TopicSummary } from "@/lib/types";

export function TopicCard({ topic }: { topic: TopicSummary }) {
  const refreshMutation = useRefreshTopic();
  const deleteMutation = useDeleteTopic();
  const updateMutation = useUpdateTopic();
  const [isEditing, setIsEditing] = useState(false);
  const [labelDraft, setLabelDraft] = useState(topic.label);
  const [groupDrafts, setGroupDrafts] = useState<string[]>(buildInitialGroupDrafts(topic));
  const [excludedDraft, setExcludedDraft] = useState(formatKeywordList(topic.excluded_keywords));
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    if (isEditing) {
      return;
    }

    setLabelDraft(topic.label);
    setGroupDrafts(buildInitialGroupDrafts(topic));
    setExcludedDraft(formatKeywordList(topic.excluded_keywords));
    setEditError(null);
  }, [isEditing, topic.id, topic.label, topic.search_queries, topic.keyword_groups, topic.excluded_keywords]);

  function startEditing() {
    setLabelDraft(topic.label);
    setGroupDrafts(buildInitialGroupDrafts(topic));
    setExcludedDraft(formatKeywordList(topic.excluded_keywords));
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

    const nextKeywordGroups = ensureKeywordGroups(
      groupDrafts.map((groupDraft) => parseKeywordList(groupDraft)),
      nextLabel
    );
    const nextExcludedKeywords = parseKeywordList(excludedDraft);
    const nextQueries = nextKeywordGroups.flat();

    setEditError(null);
    updateMutation.mutate(
      {
        topicId: topic.id,
        label: nextLabel,
        searchQueries: nextQueries,
        keywordGroups: nextKeywordGroups,
        excludedKeywords: nextExcludedKeywords,
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
                <div className="space-y-3">
                  {groupDrafts.map((groupDraft, index) => (
                    <div key={`group-${topic.id}-${index}`}>
                      <label htmlFor={`topic-group-${topic.id}-${index}`} className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                        {index === 0 ? "Match any of these" : `Must also match one of these (${index + 1})`}
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          id={`topic-group-${topic.id}-${index}`}
                          type="text"
                          value={groupDraft}
                          onChange={(event) => {
                            setGroupDrafts((current) => current.map((value, currentIndex) => currentIndex === index ? event.target.value : value));
                          }}
                          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none"
                        />
                        {groupDrafts.length > 1 && (
                          <button
                            type="button"
                            onClick={() => {
                              setGroupDrafts((current) => current.filter((_, currentIndex) => currentIndex !== index));
                            }}
                            className="rounded-lg border border-slate-300 px-2 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={() => setGroupDrafts((current) => [...current, ""])}
                    className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-xs font-medium uppercase tracking-wide text-slate-600 transition-colors hover:border-slate-400 hover:bg-slate-50"
                  >
                    Add AND group
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor={`topic-excluded-${topic.id}`} className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Must not include
                </label>
                <input
                  id={`topic-excluded-${topic.id}`}
                  type="text"
                  value={excludedDraft}
                  onChange={(event) => setExcludedDraft(event.target.value)}
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

              <div className="mt-3 space-y-2">
                {topic.keyword_groups.map((group, index) => (
                  <div key={`${topic.id}-group-${index}`} className="flex flex-wrap gap-1.5">
                    <span className="self-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                      {index === 0 ? "Any of" : "And one of"}
                    </span>
                    {group.map((query) => (
                      <span
                        key={`${topic.id}-${index}-${query}`}
                        className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600"
                      >
                        {query}
                      </span>
                    ))}
                  </div>
                ))}
                {topic.excluded_keywords.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    <span className="self-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                      Exclude
                    </span>
                    {topic.excluded_keywords.map((query) => (
                      <span
                        key={`${topic.id}-exclude-${query}`}
                        className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs text-red-700"
                      >
                        {query}
                      </span>
                    ))}
                  </div>
                )}
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
