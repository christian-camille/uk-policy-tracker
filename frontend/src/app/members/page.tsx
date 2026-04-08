"use client";

import { formatDistanceToNow } from "date-fns";
import { Clock, RefreshCw, Search, Trash2, Users, Vote } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  useRefreshAllMembers,
  useRefreshMember,
  useTrackMember,
  useTrackedMembers,
  useUntrackMember,
} from "@/hooks/useMembers";
import { api } from "@/lib/api";
import type { MemberSearchResult, TrackedMemberSummary } from "@/lib/types";

function MemberSearchPanel() {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState<MemberSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const trackMutation = useTrackMember();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (searchQuery.length < 2) {
      setResults([]);
      return;
    }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setIsSearching(true);
      try {
        const data = await api.searchMembers(searchQuery);
        setResults(data.results);
      } catch {
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 350);

    return () => clearTimeout(debounceRef.current);
  }, [searchQuery]);

  return (
    <div className="mb-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <label htmlFor="member-search" className="mb-2 block text-sm font-medium text-slate-700">
        Search for an MP, Lord, or constituency
      </label>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          id="member-search"
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder='e.g. "Keir Starmer", "Sunak", or "Leeds"'
          className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-10 pr-3 text-sm outline-none transition focus:border-indigo-500"
        />
      </div>

      {isSearching && (
        <p className="mt-3 text-sm text-slate-500">Searching...</p>
      )}

      {results.length > 0 && (
        <ul className="mt-3 divide-y divide-slate-100">
          {results.map((member) => (
            <li key={member.parliament_id} className="flex items-center justify-between gap-3 py-3">
              <div className="flex items-center gap-3">
                {member.thumbnail_url ? (
                  <img
                    src={member.thumbnail_url}
                    alt=""
                    className="h-10 w-10 rounded-full object-cover"
                  />
                ) : (
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-500">
                    {member.name_display.charAt(0)}
                  </span>
                )}
                <div>
                  <p className="text-sm font-medium text-slate-900">{member.name_display}</p>
                  <p className="text-xs text-slate-500">
                    {[member.party, member.constituency, member.house].filter(Boolean).join(" · ")}
                  </p>
                </div>
              </div>
              {member.is_tracked ? (
                <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
                  Tracked
                </span>
              ) : (
                <button
                  onClick={() => trackMutation.mutate(member.parliament_id)}
                  disabled={trackMutation.isPending}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  Track
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {searchQuery.length >= 2 && !isSearching && results.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">No members found for &quot;{searchQuery}&quot;.</p>
      )}
    </div>
  );
}

function MemberCard({ member }: { member: TrackedMemberSummary }) {
  const refreshMutation = useRefreshMember();
  const untrackMutation = useUntrackMember();

  return (
    <div className="group rounded-xl border border-slate-200 bg-white shadow-sm transition-all hover:border-slate-300 hover:shadow-md">
      <div className="h-1 rounded-t-xl bg-gradient-to-r from-emerald-500 to-teal-400" />

      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <Link
            href={`/members/${member.parliament_id}`}
            className="flex items-center gap-3"
          >
            {member.thumbnail_url ? (
              <img
                src={member.thumbnail_url}
                alt=""
                className="h-12 w-12 rounded-full object-cover"
              />
            ) : (
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-lg font-semibold text-slate-500">
                {member.name_display.charAt(0)}
              </span>
            )}
            <div>
              <p className="text-base font-semibold text-slate-900 group-hover:text-indigo-700">
                {member.name_display}
              </p>
              <p className="text-xs text-slate-500">
                {[member.party, member.constituency].filter(Boolean).join(" · ")}
              </p>
            </div>
          </Link>

          <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
            <button
              onClick={() => refreshMutation.mutate(member.parliament_id)}
              disabled={refreshMutation.isPending}
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-indigo-50 hover:text-indigo-600 disabled:opacity-50"
              title="Refresh member data"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => {
                if (confirm(`Stop tracking "${member.name_display}"?`)) {
                  untrackMutation.mutate(member.parliament_id);
                }
              }}
              disabled={untrackMutation.isPending}
              className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
              title="Stop tracking"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
          {member.house && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {member.house}
            </span>
          )}
          {!member.is_active && (
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
              Inactive
            </span>
          )}
        </div>

        <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1">
            <Vote className="h-3 w-3" />
            {member.vote_count} votes
          </span>
          <span>{member.question_count} questions</span>
        </div>

        <div className="mt-2 flex items-center gap-1 text-xs text-slate-400">
          <Clock className="h-3 w-3" />
          {member.last_refreshed_at
            ? `Updated ${formatDistanceToNow(new Date(member.last_refreshed_at), { addSuffix: true })}`
            : "Never refreshed"}
        </div>
      </div>
    </div>
  );
}

export default function MembersPage() {
  const { data, isLoading, error } = useTrackedMembers();
  const refreshAllMutation = useRefreshAllMembers();
  const [showSearch, setShowSearch] = useState(false);

  const members = data?.members ?? [];

  return (
    <main>
      <div className="border-b border-slate-200/60 bg-gradient-to-b from-slate-100 via-slate-50/80 to-transparent pb-6 pt-8">
        <div className="mx-auto max-w-6xl px-6">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            MP Watchlist
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500">
            Track individual MPs to see their voting records and parliamentary questions.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-slate-900">Tracked Members</h2>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
              {members.length}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => refreshAllMutation.mutate()}
              disabled={refreshAllMutation.isPending || members.length === 0}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm transition-colors hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${refreshAllMutation.isPending ? "animate-spin" : ""}`}
              />
              {refreshAllMutation.isPending ? "Refreshing..." : "Refresh All"}
            </button>
            <button
              onClick={() => setShowSearch((c) => !c)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
            >
              <Search className="h-3.5 w-3.5" />
              {showSearch ? "Cancel" : "Add Member"}
            </button>
          </div>
        </div>

        {refreshAllMutation.isPending && (
          <div className="mb-4 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-900">
            Refreshing all tracked members. Fetching latest profiles and voting records from Parliament.
          </div>
        )}

        {refreshAllMutation.isError && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            Failed to refresh members. Try again later.
          </div>
        )}

        {refreshAllMutation.isSuccess && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-900">
            Refresh completed for {(refreshAllMutation.data as { members: number }).members} member
            {(refreshAllMutation.data as { members: number }).members === 1 ? "" : "s"}.
          </div>
        )}

        {showSearch && <MemberSearchPanel />}

        {isLoading && <div className="py-12 text-center text-slate-500">Loading members...</div>}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            Failed to load members. Is the API running?
          </div>
        )}

        {!isLoading && !error && members.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
              <Users className="h-6 w-6 text-indigo-400" />
            </div>
            <h3 className="text-base font-semibold text-slate-900">No members tracked</h3>
            <p className="mt-1 max-w-sm text-sm text-slate-500">
              Search for an MP to start tracking their votes and questions.
            </p>
            <button
              onClick={() => setShowSearch(true)}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
            >
              <Search className="h-4 w-4" />
              Find an MP
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {members.map((member) => (
            <MemberCard key={member.parliament_id} member={member} />
          ))}
        </div>
      </div>
    </main>
  );
}
