"use client";

import { formatDistanceToNow } from "date-fns";
import { Clock, Pencil, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useDeleteTopic, useRefreshTopic, useUpdateTopic } from "@/hooks/useTopics";
import { buildInitialGroupDrafts, ensureKeywordGroups, formatKeywordList, parseKeywordList } from "@/lib/topicRules";
import { TopicSummary } from "@/lib/types";

export function TopicCard({ topic }: { topic: TopicSummary }) {
  const refreshMutation = useRefreshTopic();
  const deleteMutation = useDeleteTopic();
  const updateMutation = useUpdateTopic();
  const [isEditing, setIsEditing] = useState(false);
  const [showAllKeywords, setShowAllKeywords] = useState(false);
  const [labelDraft, setLabelDraft] = useState(topic.label);
  const [groupDrafts, setGroupDrafts] = useState<string[]>(buildInitialGroupDrafts(topic));
  const [excludedDraft, setExcludedDraft] = useState(formatKeywordList(topic.excluded_keywords));
  const [editError, setEditError] = useState<string | null>(null);

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

  const hasExtraKeywords = topic.keyword_groups.length > 1 || topic.excluded_keywords.length > 0;

  if (isEditing) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="h-1 rounded-t-xl bg-gradient-to-r from-indigo-500 to-indigo-400" />
        <div className="p-5">
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
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-400 focus:outline-none"
              />
            </div>

            <div className="space-y-3">
              {groupDrafts.map((groupDraft, index) => (
                <div key={`group-${topic.id}-${index}`}>
                  <label htmlFor={`topic-group-${topic.id}-${index}`} className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                    {index === 0 ? "Include any of these" : `Require at least one of these (${index + 1})`}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      id={`topic-group-${topic.id}-${index}`}
                      type="text"
                      value={groupDraft}
                      onChange={(event) => {
                        setGroupDrafts((current) => current.map((value, currentIndex) => currentIndex === index ? event.target.value : value));
                      }}
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-400 focus:outline-none"
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
                Add required group
              </button>
            </div>

            <div>
              <label htmlFor={`topic-excluded-${topic.id}`} className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                Exclude any of these
              </label>
              <input
                id={`topic-excluded-${topic.id}`}
                type="text"
                value={excludedDraft}
                onChange={(event) => setExcludedDraft(event.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-400 focus:outline-none"
              />
            </div>

            {editError && <p className="text-sm text-red-700">{editError}</p>}

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={saveTopicEdits}
                disabled={updateMutation.isPending}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
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
        </div>
      </div>
    );
  }

  return (
    <div className="group rounded-xl border border-slate-200 bg-white shadow-sm transition-all hover:border-slate-300 hover:shadow-md">
      <div className="h-1 rounded-t-xl bg-gradient-to-r from-indigo-500 to-indigo-400" />

      <div className="p-5">
        {/* Topic name + hover actions */}
        <div className="flex items-start justify-between gap-3">
          <Link
            href={`/topics/${topic.id}`}
            className="text-base font-semibold text-slate-900 hover:text-indigo-700"
          >
            {topic.label}
          </Link>

          <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
            <button
              onClick={startEditing}
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              title="Edit topic"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => refreshMutation.mutate(topic.id)}
              disabled={refreshMutation.isPending}
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-indigo-50 hover:text-indigo-600 disabled:opacity-50"
              title="Refresh topic data"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => {
                if (confirm(`Remove "${topic.label}" from your watchlist?`)) {
                  deleteMutation.mutate(topic.id);
                }
              }}
              disabled={deleteMutation.isPending}
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
              title="Remove topic"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Metadata row */}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {topic.last_refreshed_at
              ? `Updated ${formatDistanceToNow(new Date(topic.last_refreshed_at), { addSuffix: true })}`
              : "Never refreshed"}
          </span>
          {topic.new_items_count > 0 && (
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
              {topic.new_items_count} new
            </span>
          )}
        </div>

        {/* Keywords */}
        {topic.keyword_groups.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {/* First keyword group always visible */}
            <div className="flex flex-wrap gap-1">
              {topic.keyword_groups[0].map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                >
                  {keyword}
                </span>
              ))}
            </div>

            {/* Toggle for extra groups */}
            {hasExtraKeywords && (
              <button
                onClick={() => setShowAllKeywords((c) => !c)}
                className="text-xs font-medium text-slate-400 hover:text-slate-600"
              >
                {showAllKeywords
                  ? "Show less"
                  : `+${topic.keyword_groups.length - 1} more group${topic.keyword_groups.length > 2 ? "s" : ""}${
                      topic.excluded_keywords.length > 0
                        ? `, ${topic.excluded_keywords.length} excluded`
                        : ""
                    }`}
              </button>
            )}

            {/* Expanded keyword groups */}
            {showAllKeywords && (
              <>
                {topic.keyword_groups.slice(1).map((group, index) => (
                  <div key={`group-${index + 1}`}>
                    <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Require one of:
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {group.map((keyword) => (
                        <span key={keyword} className="rounded-md bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
                {topic.excluded_keywords.length > 0 && (
                  <div>
                    <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                      Excluded:
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {topic.excluded_keywords.map((keyword) => (
                        <span key={keyword} className="rounded-md bg-red-50 px-2 py-0.5 text-xs text-red-600">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
