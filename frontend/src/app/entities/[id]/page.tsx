"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ConnectionList } from "@/components/ConnectionList";
import { useEntity } from "@/hooks/useEntity";

type EntityProperties = Record<string, unknown>;

function getString(properties: EntityProperties | null | undefined, key: string) {
  const value = properties?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function renderGenericProperties(properties: EntityProperties) {
  return (
    <dl className="grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
      {Object.entries(properties).map(([key, value]) => {
        if (value === null || value === undefined) {
          return null;
        }

        const isLongText = key === "question_text" || key === "answer_text";

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
  );
}

function QuestionDetail({
  label,
  properties,
}: {
  label: string;
  properties: EntityProperties;
}) {
  const questionText = getString(properties, "question_text");
  const answerText = getString(properties, "answer_text");
  const answerSourceUrl = getString(properties, "answer_source_url");
  const detailPairs = [
    ["Status", getString(properties, "status")],
    ["UIN", getString(properties, "uin")],
    ["House", getString(properties, "house")],
    ["Asked by", getString(properties, "asked_by")],
    ["Answering body", getString(properties, "answering_body")],
    ["Tabled", getString(properties, "date_tabled")],
    ["Answered", getString(properties, "date_answered")],
  ].filter(([, value]) => Boolean(value));

  return (
    <div className="mb-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 bg-[radial-gradient(circle_at_top_left,_rgba(15,118,110,0.14),_transparent_40%),linear-gradient(135deg,#f8fafc_0%,#ffffff_55%,#ecfeff_100%)] px-6 py-6">
        <div className="mb-3 flex items-center gap-3">
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide text-emerald-700">
            Parliamentary Question
          </span>
        </div>
        <h1 className="max-w-3xl text-2xl font-bold text-slate-950">{label}</h1>
      </div>

      <div className="space-y-6 p-6">
        {detailPairs.length > 0 && (
          <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
            {detailPairs.map(([labelText, value]) => (
              <div key={labelText}>
                <dt className="text-slate-500">{labelText}</dt>
                <dd className="mt-1 font-medium text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>
        )}

        {questionText && (
          <section className="rounded-xl border border-slate-200 bg-slate-50 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
              Question
            </h2>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-800">
              {questionText}
            </p>
          </section>
        )}

        {answerText && (
          <section className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">
                Answer
              </h2>
              {answerSourceUrl && (
                <a
                  href={answerSourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-emerald-800 underline decoration-emerald-300 underline-offset-2 hover:text-emerald-950"
                >
                  Open referenced source
                </a>
              )}
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-900">
              {answerText}
            </p>
          </section>
        )}
      </div>
    </div>
  );
}

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
          {data.node.entity_type === "question" && data.node.properties ? (
            <QuestionDetail label={data.node.label} properties={data.node.properties} />
          ) : (
            <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-3 flex items-center gap-3">
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                  {data.node.entity_type}
                </span>
              </div>
              <h1 className="mb-3 text-2xl font-bold text-slate-900">{data.node.label}</h1>

              {data.node.properties && Object.keys(data.node.properties).length > 0 && (
                renderGenericProperties(data.node.properties)
              )}
            </div>
          )}

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
