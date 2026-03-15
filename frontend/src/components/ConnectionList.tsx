import Link from "next/link";
import { GraphEdge } from "@/lib/types";

export function ConnectionList({ connections }: { connections: GraphEdge[] }) {
  if (connections.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
        No connections found for this entity.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {connections.map((connection, index) => (
        <Link
          key={`${connection.direction}-${connection.edge_type}-${connection.connected_node.id}-${index}`}
          href={`/entities/${connection.connected_node.id}`}
          className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                {connection.direction} • {connection.edge_type.replace(/_/g, " ")}
              </p>
              <h3 className="mt-1 font-medium text-slate-900">
                {connection.connected_node.label}
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                {connection.connected_node.entity_type.replace(/_/g, " ")}
              </p>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
