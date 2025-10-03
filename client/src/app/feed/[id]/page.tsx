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

type FeedRes = {
  id: string;
  status: string;
  partial: boolean;
  product?: { id: string; name: string; description: string };
  suggestions: Suggestion[];
  steps: { step_name: string; status: string }[];
};

export default function FeedPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const guest_id = search.get("guest_id") || "";
  const [data, setData] = useState<FeedRes | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [articlesBySuggestion, setArticlesBySuggestion] = useState<Record<string, {
    loading: boolean;
    articleId?: string;
    article?: {
      id: string;
      title: string;
      content_html?: string | null;
      content_md?: string | null;
      status: string;
      error?: string | null;
    };
    error?: string | null;
  }>>({});

  useEffect(() => {
    let timer: any;
    async function fetchFeed() {
      try {
        // Use reports endpoint, but alias exists at /api/feeds/<id>
        const res = await api.get(`/api/feeds/${params.id}?guest_id=${encodeURIComponent(guest_id)}`);
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error || "Failed to load feed");
        setData(json);
        if (json.status === "queued" || json.status === "running") {
          timer = setTimeout(fetchFeed, 2000);
        }
      } catch (e: any) {
        setError(e.message || "Error");
      }
    }
    fetchFeed();
    return () => timer && clearTimeout(timer);
  }, [params.id, guest_id]);

  async function generateNewForProduct() {
    if (!data?.product?.id) return;
    setCreating(true);
    setError(null);
    try {
      const res = await api.post(`/api/products/${data.product.id}/feeds/initiate`, {});
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Failed to initiate");
      window.location.href = `/feed/${json.report_id}`;
    } catch (e: any) {
      setError(e.message || "Failed to initiate");
    } finally {
      setCreating(false);
    }
  }

  async function startGenerateArticle(suggestionId: string) {
    // Prevent duplicate clicks
    setArticlesBySuggestion((prev) => ({
      ...prev,
      [suggestionId]: { ...(prev[suggestionId] || {}), loading: true, error: null },
    }));
    try {
      const res = await api.post(`/api/articles`, { suggestion_id: suggestionId });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Failed to start generation");
      const articleId: string = json.article_id;
      setArticlesBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: true, articleId },
      }));
      // Poll until ready/failed
      await pollArticleUntilReady(suggestionId, articleId);
    } catch (e: any) {
      setArticlesBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, error: e.message || "Failed" },
      }));
    }
  }

  async function pollArticleUntilReady(suggestionId: string, articleId: string) {
    let attempts = 0;
    const maxAttempts = 600; // ~15 mins at 1.5s interval
    async function tick() {
      attempts += 1;
      try {
        const res = await api.get(`/api/articles/${articleId}`);
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error || "Fetch failed");
        const status = json.status as string;
        if (status === "ready" || status === "failed") {
          setArticlesBySuggestion((prev) => ({
            ...prev,
            [suggestionId]: {
              ...(prev[suggestionId] || {}),
              loading: false,
              articleId,
              article: json,
              error: status === "failed" ? (json.error || "Generation failed") : null,
            },
          }));
          return;
        }
      } catch (e: any) {
        // keep polling but record transient error
        setArticlesBySuggestion((prev) => ({
          ...prev,
          [suggestionId]: { ...(prev[suggestionId] || {}), error: e.message || "Error fetching article" },
        }));
      }
      if (attempts < maxAttempts) {
        setTimeout(tick, 1500);
      } else {
        setArticlesBySuggestion((prev) => ({
          ...prev,
          [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, error: "Timed out" },
        }));
      }
    }
    setTimeout(tick, 1500);
  }

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
              <div className="mt-4 rounded-xl border p-5 bg-gray-50">
                <h2 className="text-xl font-semibold">{data.product.name}</h2>
                <p className="text-gray-700 mt-2 whitespace-pre-wrap">{data.product.description}</p>
                <div className="mt-4 flex gap-2">
                  <button onClick={generateNewForProduct} disabled={creating} className="rounded-md bg-black text-white px-4 py-2 hover:bg-gray-900 disabled:opacity-50">{creating ? "Starting…" : "Generate new feed"}</button>
                  <a href={`/product/${data.product.id}`} className="rounded-md border px-4 py-2 hover:bg-gray-50">Browse old feeds</a>
                </div>
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
                    {isHeadline && s.meta?.description && (
                      <div className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">{s.meta.description}</div>
                    )}
                    {s.meta?.reason && (
                      <div className="mt-2 text-xs text-gray-600">Reason: {s.meta.reason}</div>
                    )}
                    {isHeadline && (
                      <div className="mt-3 flex items-center gap-3">
                        {(() => {
                          const st = articlesBySuggestion[s.id];
                          const loading = !!st?.loading;
                          const hasArticle = !!st?.article && st.article.status === "ready";
                          const failed = st?.article?.status === "failed";
                          return (
                            <>
                              <button
                                onClick={() => startGenerateArticle(s.id)}
                                disabled={loading}
                                className="inline-flex items-center gap-2 rounded-md bg-white border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
                                title="Generate full article"
                              >
                                <span>🌬️</span>
                                <span>{loading ? "Generating…" : "Generate article"}</span>
                              </button>
                              {failed && (
                                <span className="text-xs text-red-600">{st?.error || "Generation failed"}</span>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    )}
                    {isHeadline && (() => {
                      const st = articlesBySuggestion[s.id];
                      const art = st?.article;
                      if (!art || art.status !== "ready") return null;
                      return (
                        <div className="mt-4 rounded-md border bg-gray-50 p-4">
                          <div className="text-base font-semibold">{art.title}</div>
                          {art.content_html ? (
                            <div className="prose max-w-none mt-2" dangerouslySetInnerHTML={{ __html: art.content_html }} />
                          ) : (
                            <pre className="mt-2 whitespace-pre-wrap text-sm text-gray-800">{art.content_md}</pre>
                          )}
                        </div>
                      );
                    })()}
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
