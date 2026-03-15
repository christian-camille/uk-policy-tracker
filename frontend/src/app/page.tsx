"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { TopicCard } from "@/components/TopicCard";
import { useCreateTopic, useTopics } from "@/hooks/useTopics";

export default function WatchlistPage() {
  const { data, isLoading, error } = useTopics();
  const createMutation = useCreateTopic();
  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [queries, setQueries] = useState("");

  const topics = data?.topics ?? [];

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!label.trim()) {
      return;
    }

    const searchQueries = queries
      .split(",")
      .map((query) => query.trim())
      .filter(Boolean);

    if (searchQueries.length === 0) {
      searchQueries.push(label.trim());
    }

    createMutation.mutate(
      {
        label: label.trim(),
        searchQueries,
      },
      {
        onSuccess: () => {
          setLabel("");
          setQueries("");
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
          <button
            onClick={() => setShowForm((current) => !current)}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700"
          >
            <Plus className="h-4 w-4" />
            {showForm ? "Close" : "Add Topic"}
          </button>
        </div>

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
              <label htmlFor="queries" className="mb-1 block text-sm font-medium text-slate-700">
                Search queries
                <span className="ml-1 font-normal text-slate-400">(comma-separated, defaults to topic name)</span>
              </label>
              <input
                id="queries"
                type="text"
                value={queries}
                onChange={(event) => setQueries(event.target.value)}
                placeholder='e.g. "planning reform, local government"'
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

        <div className="space-y-4">
          {topics.map((topic) => (
            <TopicCard key={topic.id} topic={topic} />
          ))}
        </div>
      </section>
    </main>
  );
}
