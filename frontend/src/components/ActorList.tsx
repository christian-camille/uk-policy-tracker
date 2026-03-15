import Link from "next/link";
import { Actor } from "@/lib/types";

export function ActorList({ actors }: { actors: Actor[] }) {
  if (actors.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">
        No key actors yet.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {actors.map((actor) => (
        <Link
          key={actor.id}
          href={`/entities/${actor.id}`}
          className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-medium text-slate-900">{actor.label}</h3>
              <p className="mt-1 text-sm text-slate-500">
                {[actor.properties?.party, actor.properties?.constituency].filter(Boolean).join(" • ") || "Connected actor"}
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
              {actor.connection_count}
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
