"use client";

import Link from "next/link";
import {
  FileText,
  Users,
  Building2,
  Gavel,
  HelpCircle,
  Vote,
  Tag,
} from "lucide-react";
import { GraphEdge } from "@/lib/types";

const ENTITY_TYPE_CONFIG: Record<
  string,
  { icon: React.ElementType; color: string }
> = {
  topic: { icon: Tag, color: "text-indigo-600" },
  content_item: { icon: FileText, color: "text-blue-600" },
  organisation: { icon: Building2, color: "text-teal-600" },
  person: { icon: Users, color: "text-amber-600" },
  bill: { icon: Gavel, color: "text-purple-600" },
  question: { icon: HelpCircle, color: "text-orange-600" },
  division: { icon: Vote, color: "text-red-600" },
};

const EDGE_TYPE_LABELS: Record<string, string> = {
  PUBLISHED_BY: "Published by",
  MENTIONS: "Mentions",
  ABOUT_TOPIC: "About topic",
  ASKED_BY: "Asked by",
  SPONSORED_BY: "Sponsored by",
  MEMBER_OF: "Member of",
  VOTED_IN: "Voted in",
};

export function ConnectionList({ connections }: { connections: GraphEdge[] }) {
  if (connections.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4">No connections found.</div>
    );
  }

  // Group connections by edge_type
  const grouped = connections.reduce(
    (acc, conn) => {
      const key = conn.edge_type;
      if (!acc[key]) acc[key] = [];
      acc[key].push(conn);
      return acc;
    },
    {} as Record<string, GraphEdge[]>
  );

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([edgeType, edges]) => (
        <div key={edgeType}>
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            {EDGE_TYPE_LABELS[edgeType] ?? edgeType}{" "}
            <span className="text-gray-400">({edges.length})</span>
          </h3>
          <div className="space-y-1.5">
            {edges.map((edge, i) => {
              const node = edge.connected_node;
              const config = ENTITY_TYPE_CONFIG[node.entity_type] ?? {
                icon: FileText,
                color: "text-gray-600",
              };
              const Icon = config.icon;

              return (
                <Link
                  key={`${edgeType}-${i}`}
                  href={`/entities/${node.id}`}
                  className="flex items-center gap-3 p-2.5 bg-white border border-gray-200 rounded-md hover:shadow-sm transition-shadow"
                >
                  <Icon className={`w-4 h-4 shrink-0 ${config.color}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 truncate">
                      {node.label}
                    </p>
                    <p className="text-xs text-gray-400">
                      {node.entity_type} &middot; {edge.direction}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
