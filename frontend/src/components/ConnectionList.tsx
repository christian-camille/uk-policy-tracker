"use client";

import { format } from "date-fns";
import Link from "next/link";
import { useState } from "react";
import { GraphEdge } from "@/lib/types";

const ENTITY_TYPE_CONFIG: Record<
  string,
  { badgeClassName: string; label: string }
> = {
  person: {
    badgeClassName: "bg-sky-50 text-sky-700 border border-sky-200",
    label: "Person",
  },
  question: {
    badgeClassName: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    label: "Question",
  },
  bill: {
    badgeClassName: "bg-amber-50 text-amber-700 border border-amber-200",
    label: "Bill",
  },
  organisation: {
    badgeClassName: "bg-violet-50 text-violet-700 border border-violet-200",
    label: "Organisation",
  },
  content_item: {
    badgeClassName: "bg-slate-100 text-slate-700 border border-slate-200",
    label: "Publication",
  },
  division: {
    badgeClassName: "bg-rose-50 text-rose-700 border border-rose-200",
    label: "Division",
  },
  topic: {
    badgeClassName: "bg-cyan-50 text-cyan-700 border border-cyan-200",
    label: "Topic",
  },
};

const SORT_LABELS = {
  relevance: "Most useful",
  entityType: "Entity type",
  label: "Name",
} as const;

function getString(record: Record<string, unknown> | null | undefined, key: string) {
  const value = record?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function getBoolean(record: Record<string, unknown> | null | undefined, key: string) {
  const value = record?.[key];
  return typeof value === "boolean" ? value : null;
}

function getNumber(record: Record<string, unknown> | null | undefined, key: string) {
  const value = record?.[key];
  return typeof value === "number" ? value : null;
}

function formatEntityType(entityType: string) {
  return ENTITY_TYPE_CONFIG[entityType]?.label ?? entityType.replace(/_/g, " ");
}

function formatDateValue(value: string | null) {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return format(parsed, "d MMM yyyy");
}

function getConnectionSummary(connection: GraphEdge) {
  const nodeProperties = connection.connected_node.properties;
  const edgeProperties = connection.properties;

  switch (connection.connected_node.entity_type) {
    case "question": {
      const summary = [
        getString(edgeProperties, "question_uin") ?? getString(nodeProperties, "uin"),
        getString(edgeProperties, "status") ?? getString(nodeProperties, "status"),
        getString(nodeProperties, "answering_body") ?? getString(edgeProperties, "answering_body"),
      ].filter(Boolean) as string[];
      const dates = [
        formatDateValue(
          getString(edgeProperties, "date_tabled") ?? getString(nodeProperties, "date_tabled")
        )
          ? `Tabled ${formatDateValue(getString(edgeProperties, "date_tabled") ?? getString(nodeProperties, "date_tabled"))}`
          : null,
        formatDateValue(
          getString(edgeProperties, "date_answered") ?? getString(nodeProperties, "date_answered")
        )
          ? `Answered ${formatDateValue(getString(edgeProperties, "date_answered") ?? getString(nodeProperties, "date_answered"))}`
          : null,
      ].filter(Boolean) as string[];
      return {
        summary: summary.map((item, index) => (index === 1 ? item.replace(/^./, (s) => s.toUpperCase()) : item)),
        detail: dates,
      };
    }
    case "person": {
      return {
        summary: [
          getString(nodeProperties, "party"),
          getString(nodeProperties, "house"),
          getString(nodeProperties, "constituency"),
        ].filter(Boolean) as string[],
        detail: [
          getBoolean(nodeProperties, "is_active") === false ? "Inactive member" : null,
        ].filter(Boolean) as string[],
      };
    }
    case "bill": {
      return {
        summary: [
          getString(nodeProperties, "current_stage"),
          getString(nodeProperties, "current_house"),
          getBoolean(nodeProperties, "is_act") ? "Act" : null,
        ].filter(Boolean) as string[],
        detail: [],
      };
    }
    case "division": {
      const ayeCount = getNumber(nodeProperties, "aye_count");
      const noCount = getNumber(nodeProperties, "no_count");
      return {
        summary: [
          getString(nodeProperties, "house"),
          ayeCount !== null && noCount !== null ? `${ayeCount} ayes • ${noCount} noes` : null,
        ].filter(Boolean) as string[],
        detail: [],
      };
    }
    case "organisation": {
      return {
        summary: [getString(nodeProperties, "acronym")].filter(Boolean) as string[],
        detail: [],
      };
    }
    case "content_item": {
      return {
        summary: [
          getString(nodeProperties, "document_type")?.replace(/_/g, " "),
          formatDateValue(getString(nodeProperties, "public_updated_at"))
            ? `Updated ${formatDateValue(getString(nodeProperties, "public_updated_at"))}`
            : null,
        ].filter(Boolean) as string[],
        detail: [
          getNumber(edgeProperties, "confidence") !== null
            ? `Confidence ${Math.round((getNumber(edgeProperties, "confidence") ?? 0) * 100)}%`
            : null,
        ].filter(Boolean) as string[],
      };
    }
    default:
      return { summary: [], detail: [] };
  }
}

function getActionLinks(connection: GraphEdge) {
  const nodeProperties = connection.connected_node.properties;
  const edgeProperties = connection.properties;
  const links: Array<{ href: string; label: string }> = [];

  const parliamentUrl =
    getString(edgeProperties, "question_official_url") ?? getString(nodeProperties, "parliament_url");
  if (connection.connected_node.entity_type === "question" && parliamentUrl) {
    links.push({ href: parliamentUrl, label: "Open Parliament record" });
  }

  const answerSourceUrl = getString(nodeProperties, "answer_source_url");
  if (connection.connected_node.entity_type === "question" && answerSourceUrl) {
    links.push({ href: answerSourceUrl, label: "Open referenced source" });
  }

  const govukUrl = getString(nodeProperties, "govuk_url");
  if (connection.connected_node.entity_type === "content_item" && govukUrl) {
    links.push({ href: govukUrl, label: "Open GOV.UK source" });
  }

  return links;
}

function compareConnections(a: GraphEdge, b: GraphEdge, sortMode: keyof typeof SORT_LABELS, focusEntityType?: string) {
  if (sortMode === "label") {
    return a.connected_node.label.localeCompare(b.connected_node.label);
  }

  if (sortMode === "entityType") {
    return (
      a.connected_node.entity_type.localeCompare(b.connected_node.entity_type) ||
      a.connected_node.label.localeCompare(b.connected_node.label)
    );
  }

  const defaultRank: Record<string, number> = focusEntityType === "person"
    ? { question: 0, content_item: 1, bill: 2, division: 3, organisation: 4, person: 5, topic: 6 }
    : { person: 0, question: 1, content_item: 2, bill: 3, division: 4, organisation: 5, topic: 6 };

  const aRank = defaultRank[a.connected_node.entity_type] ?? 99;
  const bRank = defaultRank[b.connected_node.entity_type] ?? 99;
  return aRank - bRank || a.connected_node.label.localeCompare(b.connected_node.label);
}

export function ConnectionList({
  connections,
  focusEntityType,
}: {
  connections: GraphEdge[];
  focusEntityType?: string;
}) {
  const [entityFilter, setEntityFilter] = useState("all");
  const [directionFilter, setDirectionFilter] = useState("all");
  const [sortMode, setSortMode] = useState<keyof typeof SORT_LABELS>("relevance");

  if (connections.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
        No connections found for this entity.
      </div>
    );
  }

  const entityTypes = Array.from(
    new Set(connections.map((connection) => connection.connected_node.entity_type))
  ).sort();

  const visibleConnections = [...connections]
    .filter((connection) => {
      if (entityFilter !== "all" && connection.connected_node.entity_type !== entityFilter) {
        return false;
      }
      if (directionFilter !== "all" && connection.direction !== directionFilter) {
        return false;
      }
      return true;
    })
    .sort((a, b) => compareConnections(a, b, sortMode, focusEntityType));

  return (
    <div className="space-y-4">
      {connections.length > 1 && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-900">Connection tools</p>
              <p className="text-sm text-slate-500">
                Showing {visibleConnections.length} of {connections.length} connections
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Entity type
                <select
                  value={entityFilter}
                  onChange={(event) => setEntityFilter(event.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-700"
                >
                  <option value="all">All</option>
                  {entityTypes.map((entityType) => (
                    <option key={entityType} value={entityType}>
                      {formatEntityType(entityType)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Direction
                <select
                  value={directionFilter}
                  onChange={(event) => setDirectionFilter(event.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-700"
                >
                  <option value="all">All</option>
                  <option value="incoming">Incoming</option>
                  <option value="outgoing">Outgoing</option>
                </select>
              </label>
              <label className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Sort
                <select
                  value={sortMode}
                  onChange={(event) => setSortMode(event.target.value as keyof typeof SORT_LABELS)}
                  className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-700"
                >
                  {Object.entries(SORT_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        </div>
      )}

      {visibleConnections.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
          No connections match the current filters.
        </div>
      ) : visibleConnections.map((connection, index) => {
        const entityConfig = ENTITY_TYPE_CONFIG[connection.connected_node.entity_type] ?? {
          badgeClassName: "bg-slate-100 text-slate-700 border border-slate-200",
          label: formatEntityType(connection.connected_node.entity_type),
        };
        const summary = getConnectionSummary(connection);
        const actionLinks = getActionLinks(connection);

        return (
        <div
          key={`${connection.direction}-${connection.edge_type}-${connection.connected_node.id}-${index}`}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide ${entityConfig.badgeClassName}`}>
                  {entityConfig.label}
                </span>
                <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                  {connection.direction}
                </span>
                <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
                  {connection.edge_type.replace(/_/g, " ")}
                </span>
              </div>

              <Link
                href={`/entities/${connection.connected_node.id}`}
                className="text-base font-semibold text-slate-900 hover:text-blue-800 hover:underline"
              >
                {connection.connected_node.label}
              </Link>

              {summary.summary.length > 0 && (
                <p className="mt-2 text-sm text-slate-600">{summary.summary.join(" • ")}</p>
              )}

              {summary.detail.length > 0 && (
                <p className="mt-1 text-sm text-slate-500">{summary.detail.join(" • ")}</p>
              )}

              {actionLinks.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
                  {actionLinks.map((link) => (
                    <a
                      key={`${connection.connected_node.id}-${link.href}`}
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-medium text-blue-700 underline decoration-blue-200 underline-offset-2 hover:text-blue-900"
                    >
                      {link.label}
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        );
      })}
    </div>
  );
}
