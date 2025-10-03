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
  meta?: any | null;
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
        <h1 className="text-3xl font-bold">Content Feed</h1>
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
              {data.suggestions.map((s) => {
                const isHeadline = s.kind === "article_headline";
                const isTweet = s.kind === "tweet";
                const isReply = s.kind === "tweet_reply";
                const icon = isHeadline ? "📰" : isReply ? "💬" : isTweet ? "🐦" : "✨";
                return (
                  <div key={s.id} className="rounded-lg border p-4">
                    <div className="text-xs text-gray-500 flex items-center gap-2">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-xs">{icon}</span>
                      <span className="uppercase tracking-wide">{s.source_type} • {s.kind}</span>
                    </div>
                    <div className="mt-2 text-lg whitespace-pre-wrap">{s.text}</div>
                    {s.meta?.reason && (
                      <div className="mt-2 text-xs text-gray-600">Reason: {s.meta.reason}</div>
                    )}
                    {isReply && s.meta?.source_tweet && (
                      <div className="mt-3 rounded-md bg-gray-50 p-3 text-sm">
                        <div className="flex items-center gap-2 text-gray-500 text-xs">
                          <span>Original tweet</span>
                          <span>•</span>
                          <span className="inline-flex items-center gap-1"><span>❤️</span>{s.meta.source_tweet.like_count ?? 0}</span>
                          <span className="inline-flex items-center gap-1"><span>🔁</span>{s.meta.source_tweet.retweet_count ?? 0}</span>
                          <span className="inline-flex items-center gap-1"><span>💬</span>{s.meta.source_tweet.reply_count ?? 0}</span>
                        </div>
                        {s.meta.source_tweet.user_name && (
                          <div className="mt-1 font-medium">{s.meta.source_tweet.user_name}</div>
                        )}
                        <div className="mt-1 text-gray-800 whitespace-pre-wrap">{s.meta.source_tweet.text}</div>
                        {(() => {
                          const st = s.meta?.source_tweet || {};
                          const id: string | undefined = st.id_str || st.id;
                          const handle: string | undefined = st.user_screen_name || st.screen_name || st.user_handle || st.username;
                          const url: string | null = id ? (handle ? `https://x.com/${handle}/status/${id}` : `https://x.com/i/web/status/${id}`) : (st.url || null);
                          return url ? (
                            <div className="mt-2">
                              <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline">
                                Open on X
                                <span aria-hidden>↗</span>
                              </a>
                            </div>
                          ) : null;
                        })()}
                      </div>
                    )}
                  </div>
                );
              })}
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
