"use client";

import { useState } from "react";
import { format, formatDistanceToNow } from "date-fns";
import { FileText } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { TimelineEvent } from "@/lib/types";
import { TIMELINE_EVENT_CONFIG } from "@/lib/timeline";

const MATCH_METHOD_LABELS: Record<string, string> = {
  govuk_search: "GOV.UK search",
  parliament_search: "Parliament search",
};

function formatMatchMethod(matchMethod: string | null | undefined) {
  if (!matchMethod) {
    return null;
  }

  return MATCH_METHOD_LABELS[matchMethod] ?? matchMethod.replaceAll("_", " ");
}

function formatRuleGroup(group: string[]) {
  if (group.length <= 1) {
    return group[0] ?? "";
  }

  return group.join(" or ");
}

function formatMatchedRuleGroups(ruleGroups: string[][] | null | undefined) {
  if (!ruleGroups || ruleGroups.length === 0) {
    return null;
  }

  return ruleGroups.map((group) => formatRuleGroup(group)).filter(Boolean).join(" + ");
}

export function Timeline({
  events,
  emptyMessage,
}: {
  events: TimelineEvent[];
  emptyMessage?: string;
}) {
  const [expandedAnswers, setExpandedAnswers] = useState<Record<number, boolean>>({});
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const returnTo = searchParams.toString() ? `${pathname}?${searchParams.toString()}` : pathname;

  if (events.length === 0) {
    return (
      <div className="py-12 text-center text-slate-500">
        {emptyMessage ?? "No activity events yet. Try refreshing the topic data."}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => {
        const config = TIMELINE_EVENT_CONFIG[event.event_type] ?? {
          color: "bg-slate-100 text-slate-800",
          border: "border-l-slate-300",
          icon: FileText,
          label: event.event_type,
        };
        const Icon = config.icon;
        const isQuestionEvent = event.source_entity_type === "question";
        const questionMeta = [
          event.asking_member_name ? `Asked by ${event.asking_member_name}` : null,
          event.question_house,
          event.question_uin ? `UIN ${event.question_uin}` : null,
        ].filter(Boolean);
        const matchMethod = formatMatchMethod(event.match_provenance?.match_method);
        const matchedRuleGroups = formatMatchedRuleGroups(
          event.match_provenance?.matched_by_rule_group
        );
        const showMatchProvenance = Boolean(
          matchMethod ||
            event.match_provenance?.matched_by_query ||
            matchedRuleGroups ||
            event.match_provenance?.matched_at ||
            event.match_provenance?.last_matched_at ||
            event.match_provenance?.refresh_run_id
        );
        const answerPreview = event.question_answer_text?.trim();
        const isExpanded = Boolean(expandedAnswers[event.id]);
        const shouldClampAnswer = Boolean(answerPreview) && !isExpanded;

        return (
          <div
            key={event.id}
            className={`flex gap-4 rounded-xl border border-slate-200 border-l-[3px] ${config.border} bg-white p-4 shadow-sm transition-shadow hover:shadow-md`}
          >
            <div className="mt-0.5 shrink-0">
              <Icon className="h-5 w-5 text-slate-400" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${config.color}`}>
                  {config.label}
                </span>
                <time className="text-xs text-slate-400" title={format(new Date(event.event_date), "PPpp")}>
                  {format(new Date(event.event_date), "d MMM yyyy")}
                  <span className="mx-1">·</span>
                  {formatDistanceToNow(new Date(event.event_date), {
                    addSuffix: true,
                  })}
                </time>
              </div>

              <h3 className="text-sm font-medium text-slate-900">
                {event.source_url ? (
                  <a
                    href={event.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-indigo-700 hover:underline"
                  >
                    {event.title}
                  </a>
                ) : (
                  event.title
                )}
              </h3>

              {isQuestionEvent && questionMeta.length > 0 && (
                <p className="mt-2 text-xs font-medium uppercase tracking-wide text-slate-400">
                  {questionMeta.join(" • ")}
                </p>
              )}

              {isQuestionEvent && event.question_text && (
                <p className="mt-2 line-clamp-4 whitespace-pre-line text-sm text-slate-600">
                  {event.question_text}
                </p>
              )}

              {event.summary && (
                <p className="mt-1 line-clamp-2 text-sm text-slate-500">{event.summary}</p>
              )}

              {isQuestionEvent && answerPreview && (
                <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50/70 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700">
                      Answer
                    </p>
                    {answerPreview.length > 240 && (
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedAnswers((current) => ({
                            ...current,
                            [event.id]: !current[event.id],
                          }))
                        }
                        className="text-xs font-medium text-emerald-800 underline decoration-emerald-300 underline-offset-2 hover:text-emerald-950"
                      >
                        {isExpanded ? "Collapse answer" : "Show full answer"}
                      </button>
                    )}
                  </div>
                  <p className={`mt-1 whitespace-pre-line text-sm leading-relaxed text-emerald-950 ${shouldClampAnswer ? "line-clamp-4" : ""}`}>
                    {answerPreview}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
                    {event.question_official_url && (
                      <a
                        href={event.question_official_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-xs font-medium text-emerald-800 underline decoration-emerald-300 underline-offset-2 hover:text-emerald-950"
                      >
                        Open Parliament record
                      </a>
                    )}
                    {event.question_answer_source_url && (
                      <a
                        href={event.question_answer_source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-xs font-medium text-emerald-800 underline decoration-emerald-300 underline-offset-2 hover:text-emerald-950"
                      >
                        Open referenced source
                      </a>
                    )}
                  </div>
                </div>
              )}

              {isQuestionEvent && !answerPreview && event.question_official_url && (
                <div className="mt-3">
                  <a
                    href={event.question_official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex text-xs font-medium text-emerald-800 underline decoration-emerald-300 underline-offset-2 hover:text-emerald-950"
                  >
                    Open Parliament record
                  </a>
                </div>
              )}

              {isQuestionEvent && (event.question_date_tabled || event.question_date_answered) && (
                <p className="mt-2 text-xs text-slate-400">
                  {[
                    event.question_date_tabled ? `Tabled ${format(new Date(event.question_date_tabled), "d MMM yyyy")}` : null,
                    event.question_date_answered ? `Answered ${format(new Date(event.question_date_answered), "d MMM yyyy")}` : null,
                  ]
                    .filter(Boolean)
                    .join(" • ")}
                </p>
              )}

              {showMatchProvenance && (
                <details className="mt-3 rounded-lg border border-slate-200 bg-slate-50/90 px-3 py-2 text-sm text-slate-700">
                  <summary className="cursor-pointer list-none text-xs font-medium uppercase tracking-[0.18em] text-slate-500 marker:hidden">
                    <span className="inline-flex items-center gap-2">
                      <span>Why this matches</span>
                      <span className="text-[10px] font-semibold normal-case tracking-normal text-slate-400">
                        Click to expand
                      </span>
                    </span>
                  </summary>
                  <dl className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-[auto,1fr] sm:gap-x-3">
                    {matchMethod && (
                      <>
                        <dt className="font-medium text-slate-500">Method</dt>
                        <dd>{matchMethod}</dd>
                      </>
                    )}
                    {event.match_provenance?.matched_by_query && (
                      <>
                        <dt className="font-medium text-slate-500">Query</dt>
                        <dd className="break-words">{event.match_provenance.matched_by_query}</dd>
                      </>
                    )}
                    {matchedRuleGroups && (
                      <>
                        <dt className="font-medium text-slate-500">Rule groups</dt>
                        <dd className="break-words">{matchedRuleGroups}</dd>
                      </>
                    )}
                    {event.match_provenance?.matched_at && (
                      <>
                        <dt className="font-medium text-slate-500">First matched</dt>
                        <dd>
                          {format(new Date(event.match_provenance.matched_at), "d MMM yyyy")}
                        </dd>
                      </>
                    )}
                    {event.match_provenance?.last_matched_at && (
                      <>
                        <dt className="font-medium text-slate-500">Last seen</dt>
                        <dd>
                          {format(new Date(event.match_provenance.last_matched_at), "d MMM yyyy")}
                        </dd>
                      </>
                    )}
                    {event.match_provenance?.refresh_run_id && (
                      <>
                        <dt className="font-medium text-slate-500">Refresh run</dt>
                        <dd className="font-mono text-xs text-slate-600">
                          {event.match_provenance.refresh_run_id}
                        </dd>
                      </>
                    )}
                  </dl>
                </details>
              )}

              <div className="mt-2">
                <Link
                  href={`/entities/${event.source_entity_id}?entityType=${encodeURIComponent(event.source_entity_type)}&from=${encodeURIComponent(returnTo)}`}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
                >
                  View entity details
                </Link>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
