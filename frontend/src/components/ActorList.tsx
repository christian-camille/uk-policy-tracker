"use client";

import Link from "next/link";
import { Users } from "lucide-react";
import { GraphNode } from "@/lib/types";

interface Actor {
  id: number;
  label: string;
  entity_id: number;
  properties: Record<string, unknown> | null;
  connection_count: number;
}

export function ActorList({ actors }: { actors: Actor[] }) {
  if (actors.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4">
        No key actors found yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {actors.map((actor) => (
        <Link
          key={actor.id}
          href={`/entities/${actor.id}`}
          className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg hover:shadow-sm transition-shadow"
        >
          <div className="shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
            <Users className="w-4 h-4 text-gray-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {actor.label}
            </p>
            <div className="flex gap-2 text-xs text-gray-500">
              {actor.properties?.party && (
                <span>{String(actor.properties.party)}</span>
              )}
              {actor.properties?.constituency && (
                <span>- {String(actor.properties.constituency)}</span>
              )}
            </div>
          </div>
          <span className="shrink-0 inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
            {actor.connection_count}
          </span>
        </Link>
      ))}
    </div>
  );
}
