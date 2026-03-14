"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ConnectionList } from "@/components/ConnectionList";
import { useEntity } from "@/hooks/useEntity";

export default function EntityDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const nodeId = parseInt(params.id, 10);
  const { data, isLoading, error } = useEntity(nodeId);

  return (
    <main className="max-w-4xl mx-auto p-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Watchlist
      </Link>

      {isLoading && (
        <div className="text-center py-12 text-gray-500">
          Loading entity...
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
          Failed to load entity details.
        </div>
      )}

      {data && (
        <>
          <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
            <div className="flex items-center gap-3 mb-3">
              <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                {data.node.entity_type}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-3">
              {data.node.label}
            </h1>

            {data.node.properties &&
              Object.keys(data.node.properties).length > 0 && (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  {Object.entries(data.node.properties).map(([key, value]) => {
                    if (value === null || value === undefined) return null;
                    return (
                      <div key={key}>
                        <dt className="text-gray-500 capitalize">
                          {key.replace(/_/g, " ")}
                        </dt>
                        <dd className="text-gray-900 font-medium">
                          {String(value)}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
              )}
          </div>

          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Connections
            <span className="text-sm font-normal text-gray-400 ml-2">
              ({data.connections.length})
            </span>
          </h2>
          <ConnectionList connections={data.connections} />
        </>
      )}
    </main>
  );
}
