import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Actor } from "@/lib/types";

export function ActorList({ actors }: { actors: Actor[] }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const returnTo = searchParams.toString() ? `${pathname}?${searchParams.toString()}` : pathname;

  if (actors.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
        No key actors yet.
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {actors.map((actor) => (
        <Link
          key={actor.id}
          href={`/entities/${actor.id}?from=${encodeURIComponent(returnTo)}`}
          className="group block rounded-xl border border-slate-200 bg-white shadow-sm transition-all hover:border-slate-300 hover:shadow-md"
        >
          <div className="flex items-center gap-3 p-3.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-sm font-semibold text-indigo-600 transition-colors group-hover:bg-indigo-100">
              {actor.label.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-medium text-slate-900 group-hover:text-indigo-700">
                {actor.label}
              </h3>
              <p className="mt-0.5 truncate text-xs text-slate-400">
                {[actor.properties?.party, actor.properties?.constituency].filter(Boolean).join(" · ") || "Connected actor"}
              </p>
            </div>
            <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
              {actor.connection_count}
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
