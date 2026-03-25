"use client";

import { Landmark, Plus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { TopicCard } from "@/components/TopicCard";
import { useCreateTopic, useRefreshAllTopics, useTopics } from "@/hooks/useTopics";
import { ensureKeywordGroups, parseKeywordList } from "@/lib/topicRules";

export default function WatchlistPage() {
  const { data, isLoading, error } = useTopics();
  const createMutation = useCreateTopic();
  const refreshAllMutation = useRefreshAllTopics();
  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [groupDrafts, setGroupDrafts] = useState<string[]>([""]);
  const [excludedDraft, setExcludedDraft] = useState("");

  const topics = data?.topics ?? [];

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!label.trim()) {
      return;
    }

    const keywordGroups = ensureKeywordGroups(
      groupDrafts.map((groupDraft) => parseKeywordList(groupDraft)),
      label.trim()
    );
    const excludedKeywords = parseKeywordList(excludedDraft);
    const searchQueries = keywordGroups.flat();

    createMutation.mutate(
      {
        label: label.trim(),
        searchQueries,
        keywordGroups,
        excludedKeywords,
      },
      {
        onSuccess: () => {
          setLabel("");
          setGroupDrafts([""]);
          setExcludedDraft("");
          setShowForm(false);
        },
      }
    );
  };

  return (
    <main>
      {/* Gradient page header */}
      <div className="border-b border-slate-200/60 bg-gradient-to-b from-slate-100 via-slate-50/80 to-transparent pb-6 pt-8">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Policy Watchlist
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500">
            Track GOV.UK publications and parliamentary activity for the topics you care about.
          </p>
        </div>
      </div>

      {/* Content area */}
      <div className="mx-auto max-w-6xl px-6 py-6">
        {/* Section toolbar */}
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-slate-900">Tracked Topics</h2>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
              {topics.length}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => refreshAllMutation.mutate()}
              disabled={refreshAllMutation.isPending || topics.length === 0}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm transition-colors hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${refreshAllMutation.isPending ? "animate-spin" : ""}`}
              />
              {refreshAllMutation.isPending ? "Refreshing..." : "Refresh All"}
            </button>
            <button
              onClick={() => setShowForm((current) => !current)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
            >
              <Plus className="h-3.5 w-3.5" />
              {showForm ? "Cancel" : "Add Topic"}
            </button>
          </div>
        </div>

        {/* Status banners */}
        {refreshAllMutation.isPending && (
          <div className="mb-4 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-900">
            Refreshing every tracked topic. This runs GOV.UK ingest, Parliament ingest, event creation, entity matching, and graph rebuilds for each topic.
          </div>
        )}

        {refreshAllMutation.isError && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            Failed to refresh all topics. Try again after the upstream APIs recover.
          </div>
        )}

        {refreshAllMutation.isSuccess && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-900">
            {refreshAllMutation.data.topics > 0
              ? `Refresh completed for ${refreshAllMutation.data.topics} topic${refreshAllMutation.data.topics === 1 ? "" : "s"}.`
              : "No shared topics were available to refresh."}
          </div>
        )}

        {/* Add topic form */}
        {showForm && (
          <form onSubmit={handleSubmit} className="mb-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="grid gap-4">
              <div>
                <label htmlFor="label" className="mb-1 block text-sm font-medium text-slate-700">
                  Topic name
                </label>
                <input
                  id="label"
                  type="text"
                  value={label}
                  onChange={(event) => setLabel(event.target.value)}
                  placeholder='e.g. "Planning Reform"'
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ring-0 transition focus:border-indigo-500"
                  required
                />
              </div>
              <div>
                <div className="space-y-3">
                  {groupDrafts.map((groupDraft, index) => (
                    <div key={`new-group-${index}`}>
                      <label htmlFor={`queries-${index}`} className="mb-1 block text-sm font-medium text-slate-700">
                        {index === 0 ? "Include any of these" : `Require at least one of these (${index + 1})`}
                        <span className="ml-1 font-normal text-slate-400">(comma-separated, defaults to topic name)</span>
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          id={`queries-${index}`}
                          type="text"
                          value={groupDraft}
                          onChange={(event) => {
                            setGroupDrafts((current) => current.map((value, currentIndex) => currentIndex === index ? event.target.value : value));
                          }}
                          placeholder={index === 0 ? 'e.g. "planning reform, local government"' : 'e.g. "zoning, planning bill"'}
                          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ring-0 transition focus:border-indigo-500"
                        />
                        {groupDrafts.length > 1 && (
                          <button
                            type="button"
                            onClick={() => setGroupDrafts((current) => current.filter((_, currentIndex) => currentIndex !== index))}
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
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
                    className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-100"
                  >
                    Add required group
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="excluded" className="mb-1 block text-sm font-medium text-slate-700">
                  Exclude any of these
                  <span className="ml-1 font-normal text-slate-400">(comma-separated)</span>
                </label>
                <input
                  id="excluded"
                  type="text"
                  value={excludedDraft}
                  onChange={(event) => setExcludedDraft(event.target.value)}
                  placeholder='e.g. "consultation, consultation response"'
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ring-0 transition focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? "Creating..." : "Create Topic"}
                </button>
                {createMutation.isError && (
                  <p className="text-sm text-red-700">Failed to create topic.</p>
                )}
              </div>
            </div>
          </form>
        )}

        {/* Loading state */}
        {isLoading && <div className="py-12 text-center text-slate-500">Loading topics...</div>}

        {/* Error state */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            Failed to load topics. Is the API running?
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && topics.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
              <Landmark className="h-6 w-6 text-indigo-400" />
            </div>
            <h3 className="text-base font-semibold text-slate-900">No topics yet</h3>
            <p className="mt-1 max-w-sm text-sm text-slate-500">
              Add a topic to start tracking UK policy activity from GOV.UK and Parliament.
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" />
              Add Your First Topic
            </button>
          </div>
        )}

        {/* Topic grid */}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {topics.map((topic) => (
            <TopicCard key={topic.id} topic={topic} />
          ))}
        </div>
      </div>
    </main>
  );
}
