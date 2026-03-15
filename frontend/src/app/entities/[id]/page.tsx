"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ConnectionList } from "@/components/ConnectionList";
import { useEntity } from "@/hooks/useEntity";

export default function EntityDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const searchParams = useSearchParams();
  const parsedId = Number.parseInt(params.id, 10);
  const entityId = Number.isNaN(parsedId) ? undefined : parsedId;
  const entityType = searchParams.get("entityType") ?? undefined;
  const { data, isLoading, error } = useEntity(
    entityType ? { entityType, entityId } : { nodeId: entityId }
  );

  return (
    <main className="mx-auto max-w-4xl p-6">
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Watchlist
      </Link>

      {isLoading && <div className="py-12 text-center text-slate-500">Loading entity...</div>}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Failed to load entity details.
        </div>
      )}

      {data && (
        <>
          <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-3 flex items-center gap-3">
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                {data.node.entity_type}
              </span>
            </div>
            <h1 className="mb-3 text-2xl font-bold text-slate-900">{data.node.label}</h1>

            {data.node.properties && Object.keys(data.node.properties).length > 0 && (
              <dl className="grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
                {Object.entries(data.node.properties).map(([key, value]) => {
                  if (value === null || value === undefined) {
                    return null;
                  }

                  const isLongText = key === "question_text";

                  return (
                    <div key={key} className={isLongText ? "sm:col-span-2" : undefined}>
                      <dt className="capitalize text-slate-500">{key.replace(/_/g, " ")}</dt>
                      <dd className={`font-medium text-slate-900 ${isLongText ? "whitespace-pre-wrap leading-relaxed" : ""}`}>
                        {String(value)}
                      </dd>
                    </div>
                  );
                })}
              </dl>
            )}
          </div>

          <h2 className="mb-4 text-lg font-semibold text-slate-900">
            Connections
            <span className="ml-2 text-sm font-normal text-slate-400">({data.connections.length})</span>
          </h2>
          <ConnectionList connections={data.connections} />
        </>
      )}
    </main>
  );
}
