"use client";

import { ChevronDown, Search, X } from "lucide-react";
import { useState } from "react";
import { TIMELINE_EVENT_OPTIONS, TIMELINE_SOURCE_OPTIONS } from "@/lib/timeline";
import { TimelineEventType, TimelineSourceType } from "@/lib/types";

type TimelineFiltersProps = {
  since: string;
  until: string;
  query: string;
  eventTypes: TimelineEventType[];
  sourceEntityTypes: TimelineSourceType[];
  answeredOnly: boolean;
  activePresetDays: number | null;
  hasActiveFilters: boolean;
  resultCount?: number;
  isPending?: boolean;
  onSinceChange: (value: string) => void;
  onUntilChange: (value: string) => void;
  onQueryChange: (value: string) => void;
  onEventTypeToggle: (value: TimelineEventType) => void;
  onSourceTypeToggle: (value: TimelineSourceType) => void;
  onAnsweredOnlyChange: (value: boolean) => void;
  onPresetSelect: (value: number) => void;
  onClear: () => void;
};

const PRESET_DAYS = [7, 30, 90];

function pillClass(active: boolean) {
  return active
    ? "border-slate-900 bg-slate-900 text-white"
    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50";
}

export function TimelineFilters({
  since,
  until,
  query,
  eventTypes,
  sourceEntityTypes,
  answeredOnly,
  activePresetDays,
  hasActiveFilters,
  resultCount,
  isPending,
  onSinceChange,
  onUntilChange,
  onQueryChange,
  onEventTypeToggle,
  onSourceTypeToggle,
  onAnsweredOnlyChange,
  onPresetSelect,
  onClear,
}: TimelineFiltersProps) {
  const [isOpen, setIsOpen] = useState(true);
  const activeFilterCount =
    (since ? 1 : 0) +
    (until ? 1 : 0) +
    (query.trim() ? 1 : 0) +
    eventTypes.length +
    sourceEntityTypes.length +
    (answeredOnly ? 1 : 0);

  return (
    <section className="mb-5 rounded-2xl border border-slate-200 bg-slate-50/80 p-4 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">Filter timeline</p>
          <p className="mt-1 text-sm text-slate-500">
            {isOpen
              ? "Narrow activity by date, category, source, and text."
              : hasActiveFilters
                ? `${activeFilterCount} filter${activeFilterCount === 1 ? "" : "s"} active.`
                : "Filters hidden. Open the panel to refine the timeline."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
          {typeof resultCount === "number" && (
            <span className="rounded-full bg-white px-3 py-1 text-slate-700 shadow-sm ring-1 ring-slate-200">
              {resultCount} matching event{resultCount === 1 ? "" : "s"}
            </span>
          )}
          <button
            type="button"
            onClick={() => setIsOpen((value) => !value)}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100"
            aria-expanded={isOpen}
          >
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isOpen ? "rotate-180" : "rotate-0"}`} />
            {isOpen ? "Hide filters" : "Show filters"}
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={onClear}
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100"
            >
              <X className="h-3.5 w-3.5" />
              Clear all
            </button>
          )}
          {isPending && <span className="text-xs uppercase tracking-[0.14em] text-slate-400">Updating</span>}
        </div>
      </div>

      <div className={`grid overflow-hidden transition-all duration-300 ease-out ${isOpen ? "mt-4 grid-rows-[1fr] opacity-100" : "mt-0 grid-rows-[0fr] opacity-0"}`}>
        <div className="min-h-0 overflow-hidden">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
            <div className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Search title or summary
                </span>
                <span className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm focus-within:border-slate-400">
                  <Search className="h-4 w-4 text-slate-400" />
                  <input
                    type="search"
                    value={query}
                    onChange={(event) => onQueryChange(event.target.value)}
                    placeholder="Search events"
                    className="w-full border-0 bg-transparent p-0 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0"
                  />
                </span>
              </label>

              <div>
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Event categories
                </div>
                <div className="flex flex-wrap gap-2">
                  {TIMELINE_EVENT_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => onEventTypeToggle(option.value)}
                      className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${pillClass(eventTypes.includes(option.value))}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Source families
                </div>
                <div className="flex flex-wrap gap-2">
                  {TIMELINE_SOURCE_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => onSourceTypeToggle(option.value)}
                      className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${pillClass(sourceEntityTypes.includes(option.value))}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-4 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
              <div>
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Date range
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-1 block text-sm text-slate-600">From</span>
                    <input
                      type="date"
                      value={since}
                      onChange={(event) => onSinceChange(event.target.value)}
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-sm text-slate-600">To</span>
                    <input
                      type="date"
                      value={until}
                      onChange={(event) => onUntilChange(event.target.value)}
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-400 focus:outline-none"
                    />
                  </label>
                </div>
              </div>

              <div>
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Recent windows
                </div>
                <div className="flex flex-wrap gap-2">
                  {PRESET_DAYS.map((days) => (
                    <button
                      key={days}
                      type="button"
                      onClick={() => onPresetSelect(days)}
                      className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${pillClass(activePresetDays === days)}`}
                    >
                      Last {days} days
                    </button>
                  ))}
                </div>
              </div>

              <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={answeredOnly}
                  onChange={(event) => onAnsweredOnlyChange(event.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
                />
                <span>
                  <span className="block font-medium text-slate-900">Only answered questions</span>
                  <span className="mt-0.5 block text-slate-500">
                    Shortcut for narrowing the timeline to answered parliamentary questions.
                  </span>
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}