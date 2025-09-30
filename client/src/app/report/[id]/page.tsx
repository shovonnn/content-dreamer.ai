"use client";
import { useEffect, useState } from "react";
import { useSearchParams, useParams } from "next/navigation";
import { api } from "@/lib/apiClient";

type Suggestion = {
  id: string;
  kind: string;
  source_type: string;
  text: string;
  rank: number;
};

type ReportRes = {
  id: string;
  status: string;
  partial: boolean;
  product?: { id: string; name: string; description: string };
  suggestions: Suggestion[];
  steps: { step_name: string; status: string }[];
};

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const guest_id = search.get("guest_id") || "";
  const [data, setData] = useState<ReportRes | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: any;
    async function fetchReport() {
      try {
        const res = await api.get(`/api/reports/${params.id}?guest_id=${encodeURIComponent(guest_id)}`);
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error || "Failed to load report");
        setData(json);
        if (json.status === "queued" || json.status === "running") {
          timer = setTimeout(fetchReport, 2000);
        }
      } catch (e: any) {
        setError(e.message || "Error");
      }
    }
    fetchReport();
    return () => timer && clearTimeout(timer);
  }, [params.id, guest_id]);

  return (
    <main className="min-h-screen bg-white text-gray-900">
      <div className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="text-3xl font-bold">Your Content Report</h1>
        {error && <p className="text-red-600 mt-4">{error}</p>}
        {!data && <p className="mt-6 text-gray-600">Loading…</p>}
        {data && (
          <div className="mt-6">
            <p className="text-sm text-gray-500">Status: {data.status}{data.partial ? " (partial)" : ""}</p>
            {data.product && (
              <div className="mt-4 rounded-lg border p-4">
                <h2 className="text-xl font-semibold">{data.product.name}</h2>
                <p className="text-gray-700 mt-2 whitespace-pre-wrap">{data.product.description}</p>
              </div>
            )}
            <div className="mt-8 space-y-4">
              {data.suggestions.length === 0 && (
                <p className="text-gray-600">We’re assembling ideas… check back in a moment.</p>
              )}
              {data.suggestions.map((s) => (
                <div key={s.id} className="rounded-lg border p-4">
                  <div className="text-xs text-gray-500">{s.source_type} • {s.kind}</div>
                  <div className="mt-2 text-lg">{s.text}</div>
                </div>
              ))}
            </div>
            {data.partial && (
              <div className="mt-8 rounded-lg border p-5 bg-gray-50">
                <h3 className="font-semibold">Unlock full suggestions</h3>
                <p className="text-gray-600 mt-2">Log in and subscribe to see all ideas and generate articles.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
