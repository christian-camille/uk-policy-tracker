"use client";

import { format } from "date-fns";
import { ArrowLeft, MessageSquare, RefreshCw, Vote } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useMember, useMemberQuestions, useMemberVotes, useRefreshMember } from "@/hooks/useMembers";

export default function MemberDetailPage({
  params,
}: {
  params: { parliamentId: string };
}) {
  const parliamentId = Number.parseInt(params.parliamentId, 10);
  const { data: member, isLoading: memberLoading } = useMember(parliamentId);
  const refreshMutation = useRefreshMember();

  const [votesPage, setVotesPage] = useState(0);
  const [questionsPage, setQuestionsPage] = useState(0);
  const votesPageSize = 25;
  const questionsPageSize = 25;

  const { data: votesData, isLoading: votesLoading } = useMemberVotes(parliamentId, {
    limit: votesPageSize,
    offset: votesPage * votesPageSize,
  });
  const { data: questionsData, isLoading: questionsLoading } = useMemberQuestions(parliamentId, {
    limit: questionsPageSize,
    offset: questionsPage * questionsPageSize,
  });

  const votes = votesData?.votes ?? [];
  const votesTotal = votesData?.total ?? 0;
  const votesTotalPages = votesTotal > 0 ? Math.ceil(votesTotal / votesPageSize) : 0;

  const questions = questionsData?.questions ?? [];
  const questionsTotal = questionsData?.total ?? 0;
  const questionsTotalPages = questionsTotal > 0 ? Math.ceil(questionsTotal / questionsPageSize) : 0;

  return (
    <main>
      {/* Header */}
      <div className="border-b border-slate-200/60 bg-gradient-to-b from-emerald-50 via-slate-50/80 to-transparent pb-6 pt-6">
        <div className="mx-auto max-w-6xl px-6">
          <Link
            href="/members"
            className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-400 transition-colors hover:text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to MP Watchlist
          </Link>

          {memberLoading && (
            <div className="py-4 text-slate-500">Loading member...</div>
          )}

          {member && (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-center gap-4">
                {member.thumbnail_url ? (
                  <img
                    src={member.thumbnail_url}
                    alt=""
                    className="h-16 w-16 rounded-full object-cover ring-2 ring-white shadow"
                  />
                ) : (
                  <span className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-xl font-bold text-slate-500 ring-2 ring-white shadow">
                    {member.name_display.charAt(0)}
                  </span>
                )}
                <div>
                  <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                    {member.name_display}
                  </h1>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                    {member.party && <span>{member.party}</span>}
                    {member.constituency && (
                      <>
                        <span className="text-slate-300">·</span>
                        <span>{member.constituency}</span>
                      </>
                    )}
                    {member.house && (
                      <>
                        <span className="text-slate-300">·</span>
                        <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs ring-1 ring-slate-200">
                          {member.house}
                        </span>
                      </>
                    )}
                    {!member.is_active && (
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700 ring-1 ring-amber-200">
                        Inactive
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={() => refreshMutation.mutate(parliamentId)}
                disabled={refreshMutation.isPending}
                className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
                {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-6xl px-6 py-6">
        {refreshMutation.isPending && (
          <div className="mb-5 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-900">
            Fetching latest profile and voting records from Parliament...
          </div>
        )}

        {refreshMutation.isError && (
          <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            Refresh failed. Try again later.
          </div>
        )}

        {refreshMutation.isSuccess && (
          <div className="mb-5 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-900">
            Refresh completed.
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Voting Record */}
          <div className="lg:col-span-2">
            <div className="mb-4 flex items-center gap-3">
              <Vote className="h-5 w-5 text-slate-400" />
              <h2 className="text-lg font-semibold text-slate-900">Voting Record</h2>
              {votesTotal > 0 && (
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
                  {votesTotal}
                </span>
              )}
            </div>

            {votesLoading && <p className="text-sm text-slate-500">Loading votes...</p>}

            {!votesLoading && votes.length === 0 && (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center">
                <p className="text-sm text-slate-500">
                  No voting records yet. Click &quot;Refresh Data&quot; to fetch this MP&apos;s voting history.
                </p>
              </div>
            )}

            {votes.length > 0 && (
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead>
                    <tr className="bg-slate-50">
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                        Date
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                        Division
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
                        Vote
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">
                        Result
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {votes.map((vote) => (
                      <tr key={`${vote.division_id}`} className="transition-colors hover:bg-slate-50">
                        <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                          {format(new Date(vote.date), "d MMM yyyy")}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-900">
                          {vote.title}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-center">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              vote.vote === "aye"
                                ? "bg-green-50 text-green-700"
                                : "bg-red-50 text-red-700"
                            }`}
                          >
                            {vote.vote === "aye" ? "Aye" : "No"}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-right text-xs text-slate-500">
                          <span className="text-green-600">{vote.aye_count}</span>
                          {" / "}
                          <span className="text-red-600">{vote.no_count}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {votesTotalPages > 1 && (
                  <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-xs text-slate-500">
                      Page {votesPage + 1} of {votesTotalPages}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setVotesPage((p) => Math.max(0, p - 1))}
                        disabled={votesPage === 0}
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:opacity-50"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setVotesPage((p) => p + 1)}
                        disabled={votesPage >= votesTotalPages - 1}
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:opacity-50"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Questions */}
          <aside>
            <div className="mb-4 flex items-center gap-3">
              <MessageSquare className="h-5 w-5 text-slate-400" />
              <h2 className="text-lg font-semibold text-slate-900">Questions</h2>
              {questionsTotal > 0 && (
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
                  {questionsTotal}
                </span>
              )}
            </div>

            {questionsLoading && <p className="text-sm text-slate-500">Loading questions...</p>}

            {!questionsLoading && questions.length === 0 && (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center">
                <p className="text-sm text-slate-500">No questions found for this member.</p>
              </div>
            )}

            {questions.length > 0 && (
              <div className="space-y-3">
                {questions.map((q) => (
                  <div key={q.question_id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                    <p className="text-sm font-medium text-slate-900">{q.heading}</p>
                    {q.answering_body && (
                      <p className="mt-1 text-xs text-slate-500">To: {q.answering_body}</p>
                    )}
                    <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                      {q.date_tabled && (
                        <span>Tabled {format(new Date(q.date_tabled), "d MMM yyyy")}</span>
                      )}
                      {q.date_answered && (
                        <>
                          <span className="text-slate-300">·</span>
                          <span className="text-green-600">
                            Answered {format(new Date(q.date_answered), "d MMM yyyy")}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                ))}

                {questionsTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-slate-500">
                      Page {questionsPage + 1} of {questionsTotalPages}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setQuestionsPage((p) => Math.max(0, p - 1))}
                        disabled={questionsPage === 0}
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:opacity-50"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setQuestionsPage((p) => p + 1)}
                        disabled={questionsPage >= questionsTotalPages - 1}
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:opacity-50"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}
