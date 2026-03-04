"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { TopicCard } from "@/components/TopicCard";
import { useTopics, useCreateTopic } from "@/hooks/useTopics";
import { useCurrentUser } from "@/hooks/useAuth";

export default function WatchlistPage() {
  const { data, isLoading, error } = useTopics("all");
  const { data: userData, isLoading: authLoading } = useCurrentUser();
  const createMutation = useCreateTopic();
  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [queries, setQueries] = useState("");
  const [topicScope, setTopicScope] = useState<"shared" | "private">("private");

  const topics = data?.topics ?? [];
  const sharedTopics = topics.filter((topic) => topic.is_global);
  const privateTopics = topics.filter((topic) => !topic.is_global);
  const isAuthenticated = !!userData?.user;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) return;

    const searchQueries = queries
      .split(",")
      .map((q) => q.trim())
      .filter(Boolean);

    if (searchQueries.length === 0) {
      searchQueries.push(label.trim());
    }

    createMutation.mutate(
      {
        label: label.trim(),
        searchQueries,
        isGlobal: topicScope === "shared",
      },
      {
        onSuccess: () => {
          setLabel("");
          setQueries("");
          setShowForm(false);
          setTopicScope("private");
        },
      }
    );
  };

  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Policy Watchlist</h1>
        <button
          disabled={!isAuthenticated}
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          <Plus className="w-4 h-4" />
          Add Topic
        </button>
      </div>

      {!authLoading && !isAuthenticated && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-900">
          Sign in to create and manage your private topics.
        </div>
      )}

      {showForm && isAuthenticated && (
        <form
          onSubmit={handleSubmit}
          className="mb-6 bg-white border border-gray-200 rounded-lg p-5"
        >
          <h2 className="text-base font-semibold text-gray-900 mb-4">
            Add a topic to track
          </h2>
          <div className="space-y-4">
            <div>
              <label
                htmlFor="label"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Topic name
              </label>
              <input
                id="label"
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder='e.g. "Net Zero" or "Planning Reform"'
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                required
              />
            </div>
            <div>
              <label
                htmlFor="scope"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Topic visibility
              </label>
              <select
                id="scope"
                value={topicScope}
                onChange={(e) =>
                  setTopicScope(e.target.value as "shared" | "private")
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              >
                <option value="private">Private (only me)</option>
                <option value="shared">Shared (all users)</option>
              </select>
            </div>
            <div>
              <label
                htmlFor="queries"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Search queries{" "}
                <span className="text-gray-400 font-normal">
                  (comma-separated, defaults to topic name)
                </span>
              </label>
              <input
                id="queries"
                type="text"
                value={queries}
                onChange={(e) => setQueries(e.target.value)}
                placeholder='e.g. "net zero, carbon neutral, decarbonisation"'
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {createMutation.isPending ? "Creating..." : "Create Topic"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </form>
      )}

      {isLoading && (
        <div className="text-center py-12 text-gray-500">Loading topics...</div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
          Failed to load topics. Is the API running?
        </div>
      )}

      {data && data.topics.length === 0 && !showForm && (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg mb-2">No topics yet</p>
          <p className="text-sm">
            Click &quot;Add Topic&quot; to start tracking UK government policy
            activity.
          </p>
        </div>
      )}

      {data && data.topics.length > 0 && (
        <div className="space-y-8">
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">My Private Topics</h2>
            {privateTopics.length === 0 ? (
              <p className="text-sm text-gray-500">No private topics yet.</p>
            ) : (
              <div className="space-y-3">
                {privateTopics.map((topic) => (
                  <TopicCard key={topic.id} topic={topic} />
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Shared Topics</h2>
            {sharedTopics.length === 0 ? (
              <p className="text-sm text-gray-500">No shared topics yet.</p>
            ) : (
              <div className="space-y-3">
                {sharedTopics.map((topic) => (
                  <TopicCard key={topic.id} topic={topic} />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
