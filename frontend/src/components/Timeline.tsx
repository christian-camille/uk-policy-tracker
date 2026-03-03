"use client";

import { formatDistanceToNow } from "date-fns";
import {
  FileText,
  Gavel,
  HelpCircle,
  CheckCircle,
  Vote,
} from "lucide-react";
import Link from "next/link";
import { TimelineEvent } from "@/lib/types";

const EVENT_CONFIG: Record<
  string,
  { color: string; icon: React.ElementType; label: string }
> = {
  govuk_publication: {
    color: "bg-blue-100 text-blue-800",
    icon: FileText,
    label: "GOV.UK Publication",
  },
  bill_stage: {
    color: "bg-purple-100 text-purple-800",
    icon: Gavel,
    label: "Bill Stage",
  },
  question_tabled: {
    color: "bg-amber-100 text-amber-800",
    icon: HelpCircle,
    label: "Question Tabled",
  },
  question_answered: {
    color: "bg-green-100 text-green-800",
    icon: CheckCircle,
    label: "Question Answered",
  },
  division_held: {
    color: "bg-red-100 text-red-800",
    icon: Vote,
    label: "Division",
  },
};

export function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No activity events yet. Try refreshing the topic data.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => {
        const config = EVENT_CONFIG[event.event_type] ?? {
          color: "bg-gray-100 text-gray-800",
          icon: FileText,
          label: event.event_type,
        };
        const Icon = config.icon;

        return (
          <div
            key={event.id}
            className="bg-white border border-gray-200 rounded-lg p-4 flex gap-4"
          >
            <div className="shrink-0 mt-0.5">
              <Icon className="w-5 h-5 text-gray-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${config.color}`}
                >
                  {config.label}
                </span>
                <time className="text-xs text-gray-400">
                  {formatDistanceToNow(new Date(event.event_date), {
                    addSuffix: true,
                  })}
                </time>
              </div>

              <h3 className="font-medium text-gray-900 text-sm">
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

              {event.summary && (
                <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                  {event.summary}
                </p>
              )}

              <div className="mt-2">
                <Link
                  href={`/entities/${event.source_entity_id}`}
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
