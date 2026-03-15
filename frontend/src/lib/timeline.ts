import type { LucideIcon } from "lucide-react";
import { CheckCircle, FileText, Gavel, HelpCircle, Vote } from "lucide-react";
import type { TimelineEventType, TimelineSourceType } from "./types";

type TimelineEventConfig = {
  color: string;
  icon: LucideIcon;
  label: string;
};

export const TIMELINE_EVENT_CONFIG: Record<TimelineEventType, TimelineEventConfig> = {
  govuk_publication: {
    color: "bg-blue-100 text-blue-800",
    icon: FileText,
    label: "GOV.UK Publication",
  },
  bill_stage: {
    color: "bg-rose-100 text-rose-800",
    icon: Gavel,
    label: "Bill Stage",
  },
  question_tabled: {
    color: "bg-amber-100 text-amber-800",
    icon: HelpCircle,
    label: "Question Tabled",
  },
  question_answered: {
    color: "bg-emerald-100 text-emerald-800",
    icon: CheckCircle,
    label: "Question Answered",
  },
  division_held: {
    color: "bg-red-100 text-red-800",
    icon: Vote,
    label: "Division",
  },
};

export const TIMELINE_EVENT_OPTIONS: Array<{ value: TimelineEventType; label: string }> = [
  { value: "govuk_publication", label: "GOV.UK publications" },
  { value: "bill_stage", label: "Bill stages" },
  { value: "question_tabled", label: "Questions tabled" },
  { value: "question_answered", label: "Questions answered" },
  { value: "division_held", label: "Divisions" },
];

export const TIMELINE_SOURCE_OPTIONS: Array<{ value: TimelineSourceType; label: string }> = [
  { value: "content_item", label: "GOV.UK documents" },
  { value: "bill", label: "Bills" },
  { value: "question", label: "Questions" },
  { value: "division", label: "Divisions" },
];