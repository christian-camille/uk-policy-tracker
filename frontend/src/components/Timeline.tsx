"use client";

import { format, formatDistanceToNow } from "date-fns";
import { FileText } from "lucide-react";
import Link from "next/link";
import { TimelineEvent } from "@/lib/types";
import { TIMELINE_EVENT_CONFIG } from "@/lib/timeline";

export function Timeline({
  events,
  emptyMessage,
}: {
  events: TimelineEvent[];
  emptyMessage?: string;
}) {
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

        return (
          <div
            key={event.id}
            className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
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
                    className="hover:text-blue-700 hover:underline"
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

              <div className="mt-2">
                <Link
                  href={{
                    pathname: `/entities/${event.source_entity_id}`,
                    query: { entityType: event.source_entity_type },
                  }}
                  className="text-xs text-blue-600 hover:underline"
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
