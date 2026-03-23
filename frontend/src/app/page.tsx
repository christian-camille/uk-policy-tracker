"use client";

import { Plus, RefreshCw } from "lucide-react";
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
    <main className="mx-auto max-w-5xl p-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-400">
              Local Edition
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
              Policy Watchlist
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Track GOV.UK publications and parliamentary activity for the topics you care about, with everything stored locally in PostgreSQL.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              onClick={() => refreshAllMutation.mutate()}
              disabled={refreshAllMutation.isPending || topics.length === 0}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${refreshAllMutation.isPending ? "animate-spin" : ""}`} />
              {refreshAllMutation.isPending ? "Refreshing All..." : "Refresh All"}
            </button>
            <button
              onClick={() => setShowForm((current) => !current)}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              {showForm ? "Close" : "Add Topic"}
            </button>
          </div>
        </div>

        {refreshAllMutation.isPending && (
          <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
            Refreshing every tracked topic. This runs GOV.UK ingest, Parliament ingest, event creation, entity matching, and graph rebuilds for each topic.
          </div>
        )}

        {refreshAllMutation.isError && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            Failed to refresh all topics. Try again after the upstream APIs recover.
          </div>
        )}

        {refreshAllMutation.isSuccess && (
          <div className="mt-6 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-900">
            {refreshAllMutation.data.topics > 0
              ? `Refresh completed for ${refreshAllMutation.data.topics} topic${refreshAllMutation.data.topics === 1 ? "" : "s"}.`
              : "No shared topics were available to refresh."}
          </div>
        )}

        {showForm && (
          <form onSubmit={handleSubmit} className="mt-6 grid gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
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
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ring-0 transition focus:border-blue-500"
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
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ring-0 transition focus:border-blue-500"
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
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ring-0 transition focus:border-blue-500"
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "Creating..." : "Create Topic"}
              </button>
              {createMutation.isError && (
                <p className="text-sm text-red-700">Failed to create topic.</p>
              )}
            </div>
          </form>
        )}
      </section>

      <section className="mt-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Tracked Topics</h2>
          <p className="text-sm text-slate-500">{topics.length} total</p>
        </div>

        {isLoading && <div className="py-12 text-center text-slate-500">Loading topics...</div>}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            Failed to load topics. Is the API running?
          </div>
        )}

        {!isLoading && !error && topics.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
            No topics yet. Add one to start tracking policy activity.
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {topics.map((topic) => (
            <TopicCard key={topic.id} topic={topic} />
          ))}
        </div>
      </section>
    </main>
  );
}
