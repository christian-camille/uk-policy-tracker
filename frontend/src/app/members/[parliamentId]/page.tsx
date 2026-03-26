"use client";

import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ArrowLeft, ChevronDown, ChevronRight, ExternalLink, Landmark, MessageSquare, RefreshCw, Vote } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useMember, useMemberQuestions, useMemberVotes, useRefreshMember } from "@/hooks/useMembers";
import { api } from "@/lib/api";
import type { DivisionDetail, MemberVoteRecord, PartyBreakdown } from "@/lib/types";

/** Split a division title into bill name + remainder for display. */
function splitTitle(title: string): { primary: string; secondary: string | null } {
  const m = title.match(/^(.+?\bBill(?:\s*\((?:Lords|HL)\))?)\s*(.*)/i);
  if (!m) return { primary: title, secondary: null };
  const remainder = m[2].replace(/^[:\s]+/, "").trim();
  return { primary: m[1], secondary: remainder || null };
}

function PartyBar({ parties, label }: { parties: PartyBreakdown[]; label: string }) {
  const total = parties.reduce((sum, p) => sum + p.count, 0);
  if (total === 0) return null;

  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-slate-600">{label} ({total})</p>
      <div className="flex h-3 overflow-hidden rounded-full">
        {parties.map((p) => (
          <div
            key={p.party}
            style={{ width: `${(p.count / total) * 100}%`, backgroundColor: `#${p.colour}` }}
            title={`${p.party}: ${p.count}`}
            className="transition-all"
          />
        ))}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
        {parties.slice(0, 6).map((p) => (
          <span key={p.party} className="inline-flex items-center gap-1 text-xs text-slate-500">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: `#${p.colour}` }}
            />
            {p.abbreviation} {p.count}
          </span>
        ))}
        {parties.length > 6 && (
          <span className="text-xs text-slate-400">+{parties.length - 6} more</span>
        )}
      </div>
    </div>
  );
}

function VoteDetailPanel({ vote }: { vote: MemberVoteRecord }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["divisionDetail", vote.parliament_division_id],
    queryFn: () => api.getDivisionDetail(vote.parliament_division_id),
  });

  const parliamentUrl = `https://votes.parliament.uk/Votes/Commons/Division/${vote.parliament_division_id}`;

  if (isLoading) {
    return (
      <div className="px-4 py-4 text-sm text-slate-500">
        Loading division details...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="px-4 py-4">
        <a
          href={parliamentUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800"
        >
          View on Parliament website
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
    );
  }

  const bill = data.matched_bill;

  return (
    <div className="space-y-4 px-4 py-4">
      {/* Bill context */}
      {bill && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50/50 p-3">
          <div className="mb-1.5 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-indigo-700">
              <Landmark className="h-3 w-3" />
              Related Bill
            </span>
            {bill.is_act && (
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                Act of Parliament
              </span>
            )}
            {bill.is_defeated && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                Defeated
              </span>
            )}
            {bill.current_stage && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                {bill.current_stage}
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-slate-800">{bill.short_title}</p>
          {bill.long_title && bill.long_title !== bill.short_title && (
            <p className="mt-1 text-sm text-slate-600">{bill.long_title}</p>
          )}
          <a
            href={bill.bill_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
          >
            View bill on Parliament
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}

      {/* Stage and amendment detail */}
      {(data.division_stage || data.division_detail) && (
        <div className="flex flex-wrap gap-2 text-xs">
          {data.division_stage && (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-slate-600">
              {data.division_stage}
            </span>
          )}
          {data.division_detail && (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-slate-600">
              {data.division_detail}
            </span>
          )}
        </div>
      )}

      {data.number && (
        <p className="text-xs text-slate-500">
          Division No. {data.number}
          {data.is_deferred && <span className="ml-2 rounded bg-amber-50 px-1.5 py-0.5 text-amber-700">Deferred</span>}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <PartyBar parties={data.aye_party_breakdown} label="Ayes" />
        <PartyBar parties={data.no_party_breakdown} label="Noes" />
      </div>

      <a
        href={parliamentUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800"
      >
        View full details on Parliament website
        <ExternalLink className="h-3.5 w-3.5" />
      </a>
    </div>
  );
}

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
  const [expandedVote, setExpandedVote] = useState<number | null>(null);
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
                      <th className="w-8 px-2 py-3" />
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
                    {votes.map((vote) => {
                      const isExpanded = expandedVote === vote.division_id;
                      return (
                        <tr
                          key={vote.division_id}
                          className="group"
                        >
                          <td colSpan={5} className="p-0">
                            <button
                              type="button"
                              onClick={() => setExpandedVote(isExpanded ? null : vote.division_id)}
                              className="flex w-full items-center transition-colors hover:bg-slate-50"
                            >
                              <span className="flex w-8 shrink-0 items-center justify-center px-2 py-3">
                                <ChevronDown
                                  className={`h-3.5 w-3.5 text-slate-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                                />
                              </span>
                              <span className="whitespace-nowrap px-4 py-3 text-left text-xs text-slate-500">
                                {format(new Date(vote.date), "d MMM yyyy")}
                              </span>
                              <span className="flex-1 px-4 py-3 text-left">
                                <span className="block text-sm text-slate-900">
                                  {splitTitle(vote.title).primary}
                                </span>
                                {splitTitle(vote.title).secondary && (
                                  <span className="block text-xs text-slate-400 mt-0.5">
                                    {splitTitle(vote.title).secondary}
                                  </span>
                                )}
                              </span>
                              <span className="whitespace-nowrap px-4 py-3 text-center">
                                <span
                                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                    vote.vote === "aye"
                                      ? "bg-green-50 text-green-700"
                                      : "bg-red-50 text-red-700"
                                  }`}
                                >
                                  {vote.vote === "aye" ? "Aye" : "No"}
                                </span>
                              </span>
                              <span className="whitespace-nowrap px-4 py-3 text-right text-xs text-slate-500">
                                <span className="text-green-600">{vote.aye_count}</span>
                                {" / "}
                                <span className="text-red-600">{vote.no_count}</span>
                              </span>
                            </button>
                            {isExpanded && (
                              <div className="border-t border-slate-100 bg-slate-50/50">
                                <VoteDetailPanel vote={vote} />
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {votesTotalPages > 1 && (
                  <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-xs text-slate-500">
                      Page {votesPage + 1} of {votesTotalPages}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => { setVotesPage((p) => Math.max(0, p - 1)); setExpandedVote(null); }}
                        disabled={votesPage === 0}
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:opacity-50"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => { setVotesPage((p) => p + 1); setExpandedVote(null); }}
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
                  <Link
                    key={q.question_id}
                    href={`/entities/${q.question_id}?entityType=question&from=${encodeURIComponent(`/members/${parliamentId}`)}`}
                    className="group flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 group-hover:text-indigo-600 transition-colors">
                        {q.heading}
                      </p>
                      {q.answering_body && (
                        <p className="mt-1 text-xs text-slate-500">To: {q.answering_body}</p>
                      )}
                      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-400">
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
                        {!q.date_answered && !q.answer_text && (
                          <>
                            <span className="text-slate-300">·</span>
                            <span className="text-amber-600">Awaiting answer</span>
                          </>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-slate-300 group-hover:text-slate-500 transition-colors" />
                  </Link>
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
