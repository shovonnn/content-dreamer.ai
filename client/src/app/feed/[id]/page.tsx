"use client";
import { useEffect, useState } from "react";
import Image from "next/image";
import { useSearchParams, useParams } from "next/navigation";
import { api } from "@/lib/apiClient";
import { FaMagic } from "react-icons/fa";
import ArticleEditorModal from "@/components/ArticleEditorModal";


type SuggestionMeta = {
  description?: string;
  reason?: string;
  article_id?: string;
  meme_id?: string;
  slop_id?: string;
  instructions?: unknown;
  source_tweet?: {
    id_str?: string; id?: string; url?: string;
    user_screen_name?: string; screen_name?: string; user_handle?: string; username?: string;
    user_name?: string;
    text?: string;
    like_count?: number; retweet_count?: number; reply_count?: number;
  };
};

type Suggestion = {
  id: string;
  kind: string;
  source_type: string;
  text: string;
  rank: number;
  meta?: SuggestionMeta | null;
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
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorArticleId, setEditorArticleId] = useState<string | null>(null);
  const [memesBySuggestion, setMemesBySuggestion] = useState<Record<string, {
    loading: boolean;
    memeId?: string;
    status?: string;
    error?: string | null;
  }>>({});
  const [slopsBySuggestion, setSlopsBySuggestion] = useState<Record<string, {
    loading: boolean;
    slopId?: string;
    status?: string;
    error?: string | null;
  }>>({});

  useEffect(() => {
  let timer: ReturnType<typeof setTimeout> | undefined;
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
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Error";
        setError(msg);
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
      if (res.status === 402) {
        const msg = json?.error || "Limit reached";
        window.location.href = `/pricing?reason=${encodeURIComponent(msg)}`;
        return;
      }
      if (!res.ok) throw new Error(json?.error || "Failed to initiate");
      window.location.href = `/feed/${json.report_id}`;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to initiate";
      setError(msg);
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
      if (res.status === 402) {
        const msg = json?.error || "Limit reached";
        window.location.href = `/pricing?reason=${encodeURIComponent(msg)}`;
        return;
      }
      if (!res.ok) throw new Error(json?.error || "Failed to start generation");
      const articleId: string = json.article_id;
      setArticlesBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: true, articleId },
      }));
      // Poll until ready/failed
      await pollArticleUntilReady(suggestionId, articleId);
    } catch (e: unknown) {
      setArticlesBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, error: (e instanceof Error ? e.message : "Failed") },
      }));
    }
  }

  async function startGenerateMeme(suggestionId: string) {
    setMemesBySuggestion((prev) => ({
      ...prev,
      [suggestionId]: { ...(prev[suggestionId] || {}), loading: true, error: null },
    }));
    try {
      const res = await api.post(`/api/memes`, { suggestion_id: suggestionId });
      const json = await res.json();
      if (res.status === 402) {
        const msg = json?.error || "Limit reached";
        window.location.href = `/pricing?reason=${encodeURIComponent(msg)}`;
        return;
      }
      if (!res.ok) throw new Error(json?.error || "Failed to start meme generation");
      const memeId: string = json.meme_id;
      setMemesBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: true, memeId, status: json.status },
      }));
      await pollMemeUntilReady(suggestionId, memeId);
    } catch (e: unknown) {
      setMemesBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, error: (e instanceof Error ? e.message : "Failed") },
      }));
    }
  }

  async function pollMemeUntilReady(suggestionId: string, memeId: string) {
    let attempts = 0;
    const maxAttempts = 400; // ~10 mins
    async function tick() {
      attempts += 1;
      try {
        const res = await api.get(`/api/memes/${memeId}`);
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error || "Fetch failed");
        const status = json.status as string;
        if (status === "ready" || status === "failed") {
          setMemesBySuggestion((prev) => ({
            ...prev,
            [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, memeId, status, error: status === "failed" ? (json.error || "Generation failed") : null },
          }));
          return;
        }
      } catch (e: unknown) {
        setMemesBySuggestion((prev) => ({
          ...prev,
          [suggestionId]: { ...(prev[suggestionId] || {}), error: (e instanceof Error ? e.message : "Error fetching meme") },
        }));
      }
      if (attempts < maxAttempts) {
        setTimeout(tick, 1500);
      } else {
        setMemesBySuggestion((prev) => ({
          ...prev,
          [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, error: "Timed out" },
        }));
      }
    }
    setTimeout(tick, 1500);
  }

  async function startGenerateSlop(suggestionId: string) {
    setSlopsBySuggestion((prev) => ({
      ...prev,
      [suggestionId]: { ...(prev[suggestionId] || {}), loading: true, error: null },
    }));
    try {
      const res = await api.post(`/api/slops`, { suggestion_id: suggestionId });
      const json = await res.json();
      if (res.status === 402) {
        const msg = json?.error || "Limit reached";
        window.location.href = `/pricing?reason=${encodeURIComponent(msg)}`;
        return;
      }
      if (!res.ok) throw new Error(json?.error || "Failed to start slop generation");
      const slopId: string = json.slop_id;
      setSlopsBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: true, slopId, status: json.status },
      }));
      await pollSlopUntilReady(suggestionId, slopId);
    } catch (e: unknown) {
      setSlopsBySuggestion((prev) => ({
        ...prev,
        [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, error: (e instanceof Error ? e.message : "Failed") },
      }));
    }
  }

  async function pollSlopUntilReady(suggestionId: string, slopId: string) {
    let attempts = 0;
    const maxAttempts = 600; // ~15 mins
    async function tick() {
      attempts += 1;
      try {
        const res = await api.get(`/api/slops/${slopId}`);
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error || "Fetch failed");
        const status = json.status as string;
        if (status === "ready" || status === "failed") {
          setSlopsBySuggestion((prev) => ({
            ...prev,
            [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, slopId, status, error: status === "failed" ? (json.error || "Generation failed") : null },
          }));
          return;
        }
      } catch (e: unknown) {
        setSlopsBySuggestion((prev) => ({
          ...prev,
          [suggestionId]: { ...(prev[suggestionId] || {}), error: (e instanceof Error ? e.message : "Error fetching slop") },
        }));
      }
      if (attempts < maxAttempts) {
        setTimeout(tick, 2000);
      } else {
        setSlopsBySuggestion((prev) => ({
          ...prev,
          [suggestionId]: { ...(prev[suggestionId] || {}), loading: false, error: "Timed out" },
        }));
      }
    }
    setTimeout(tick, 2000);
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
          // If generated successfully, open in editor directly
          if (status === "ready") {
            setEditorArticleId(articleId);
            setEditorOpen(true);
          }
          return;
        }
      } catch (e: unknown) {
        // keep polling but record transient error
        setArticlesBySuggestion((prev) => ({
          ...prev,
          [suggestionId]: { ...(prev[suggestionId] || {}), error: (e instanceof Error ? e.message : "Error fetching article") },
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
    <>
    <main className="">
      <div className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="text-3xl font-bold">Content Feed</h1>
        {error && <p className="text-red-600 mt-4">{error}</p>}
        {!data && <p className="mt-6 text-gray-600">Loading…</p>}
        {data && (
          <div className="mt-6">
            <p className="text-sm">Status: {data.status}{data.partial ? " (partial)" : ""}</p>
            {data.product && (
              <div className="mt-4 rounded-xl border p-5 bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700">
                <h2 className="text-xl font-semibold">{data.product.name}</h2>
                <p className="mt-2 whitespace-pre-wrap">{data.product.description}</p>
                <div className="mt-4 flex gap-2">
                  <button onClick={generateNewForProduct} disabled={creating} className="rounded-md bg-black text-white cursor-pointer px-4 py-2 hover:bg-gray-900 disabled:opacity-50">{creating ? "Starting…" : "Generate new feed"}</button>
                  <a href={`/product/${data.product.id}`} className="rounded-md border px-4 py-2 border-slate-500 hover:bg-slate-500">Browse old feeds</a>
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
                const isMemeConcept = s.kind === "meme_concept";
                const isSlopConcept = s.kind === "slop_concept";
                const icon = isHeadline ? "📰" : isReply ? "💬" : isTweet ? "🐦" : isMemeConcept ? "🖼️" : isSlopConcept ? "🎞️" : "✨";
                return (
                  <div key={s.id} className="rounded-lg border border-slate-500 bg-slate-900 p-4">
                    <div className="text-xs text-gray-500 flex items-center gap-2">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-xs">{icon}</span>
                      <span className="uppercase tracking-wide">{s.source_type} • {s.kind}</span>
                    </div>
                    <div className="mt-2 text-lg whitespace-pre-wrap">{s.text}</div>
                    {isHeadline && s.meta?.description && (
                      <div className="mt-2 text-sm whitespace-pre-wrap">{s.meta.description}</div>
                    )}
                    {s.meta?.reason && (
                      <div className="mt-2 text-xs text-gray-600">Reason: {s.meta.reason}</div>
                    )}
                    {isHeadline && (
                      <div className="mt-3 flex items-center gap-3">
                        {(() => {
                          const st = articlesBySuggestion[s.id];
                          const loading = !!st?.loading;
                          const failed = st?.article?.status === "failed";
                          const existingArticleId = (s.meta?.article_id) as string | undefined;
                          const showOpenEditor = !!existingArticleId || (st?.article?.status === "ready" && st.article?.id);
                          const articleIdToOpen = existingArticleId || st?.article?.id || st?.articleId;
                          return (
                            <>
                              {/* Hide Generate if we already have an article id in meta */}
                              {!showOpenEditor && (
                                <button
                                  onClick={() => startGenerateArticle(s.id)}
                                  disabled={loading}
                                  className="inline-flex items-center gap-2 rounded-md bg-brand-600 border border-brand-600 px-3 py-1.5 text-sm hover:bg-brand-700 cursor-pointer disabled:opacity-50"
                                  title="Generate full article"
                                >
                                  <FaMagic />
                                  <span>{loading ? "Generating…" : "Generate article"}</span>
                                </button>
                              )}
                              {showOpenEditor && articleIdToOpen && (
                                <button
                                  onClick={() => { setEditorArticleId(articleIdToOpen); setEditorOpen(true); }}
                                  className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-slate-800 border-slate-500"
                                  title="Open in editor"
                                >
                                  ✏️
                                  <span>Open in editor</span>
                                </button>
                              )}
                              {failed && (
                                <span className="text-xs text-red-600">{st?.error || "Generation failed"}</span>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    )}
                    {isMemeConcept && (
                      <div className="mt-3 flex flex-col gap-3">
                        {(() => {
                          const st = memesBySuggestion[s.id];
                          const loading = !!st?.loading;
                          const existingMemeId = s.meta?.meme_id as string | undefined;
                          const memeId = existingMemeId || st?.memeId;
                          const isReady = st?.status === "ready" || (!!existingMemeId);
                          return (
                            <div className="flex items-center gap-3">
                              {!isReady && (
                                <button
                                  onClick={() => startGenerateMeme(s.id)}
                                  disabled={loading}
                                  className="inline-flex items-center gap-2 rounded-md bg-brand-600 border border-brand-600 px-3 py-1.5 text-sm hover:bg-brand-700 cursor-pointer disabled:opacity-50"
                                  title="Generate meme image"
                                >
                                  🪄
                                  <span>{loading ? "Generating…" : "Generate meme"}</span>
                                </button>
                              )}
                              {memeId && isReady && (
                                <a
                                  href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"}/api/memes/${memeId}/image`}
                                  target="_blank"
                                  className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-slate-800 border-slate-500"
                                >
                                  ⬇️ <span>Open/Download</span>
                                </a>
                              )}
                              {st?.status === "failed" && (
                                <span className="text-xs text-red-600">{st?.error || "Generation failed"}</span>
                              )}
                            </div>
                          );
                        })()}
                        {(() => {
                          const existingMemeId = s.meta?.meme_id as string | undefined;
                          const memeId = existingMemeId || memesBySuggestion[s.id]?.memeId;
                          const isReady = memesBySuggestion[s.id]?.status === "ready" || (!!existingMemeId);
                          if (!memeId || !isReady) return null;
                          const src = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"}/api/memes/${memeId}/image`;
                          return (
                            <div className="mt-2">
                              <Image src={src} alt="Generated meme" width={1024} height={1024} className="max-h-[420px] h-auto w-auto rounded-md border border-slate-700" />
                            </div>
                          );
                        })()}
                      </div>
                    )}
                    {isSlopConcept && (
                      <div className="mt-3 flex flex-col gap-3">
                        {(() => {
                          const st = slopsBySuggestion[s.id];
                          const loading = !!st?.loading;
                          const existingSlopId = s.meta?.slop_id as string | undefined;
                          const slopId = existingSlopId || st?.slopId;
                          const isReady = st?.status === "ready" || (!!existingSlopId);
                          return (
                            <div className="flex items-center gap-3">
                              {!isReady && (
                                <button
                                  onClick={() => startGenerateSlop(s.id)}
                                  disabled={loading}
                                  className="inline-flex items-center gap-2 rounded-md bg-brand-600 border border-brand-600 px-3 py-1.5 text-sm hover:bg-brand-700 cursor-pointer disabled:opacity-50"
                                  title="Generate AI slop video"
                                >
                                  🎞️
                                  <span>{loading ? "Generating…" : "Generate AI slop"}</span>
                                </button>
                              )}
                              {slopId && isReady && (
                                <a
                                  href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"}/api/slops/${slopId}/video`}
                                  target="_blank"
                                  className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-slate-800 border-slate-500"
                                >
                                  ⬇️ <span>Open/Download</span>
                                </a>
                              )}
                              {st?.status === "failed" && (
                                <span className="text-xs text-red-600">{st?.error || "Generation failed"}</span>
                              )}
                            </div>
                          );
                        })()}
                        {(() => {
                          const existingSlopId = s.meta?.slop_id as string | undefined;
                          const slopId = existingSlopId || slopsBySuggestion[s.id]?.slopId;
                          const isReady = slopsBySuggestion[s.id]?.status === "ready" || (!!existingSlopId);
                          if (!slopId || !isReady) return null;
                          const src = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"}/api/slops/${slopId}/video`;
                          return (
                            <div className="mt-2">
                              <video controls className="max-h-[420px] h-auto w-auto rounded-md border border-slate-700" src={src} />
                            </div>
                          );
                        })()}
                      </div>
                    )}
                    {/* Don't auto-render the article below; we'll open the editor instead */}
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
                          <div className="mt-1 text-gray-800 font-medium">{s.meta.source_tweet.user_name}</div>
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
    <ArticleEditorModal
      isOpen={editorOpen}
      articleId={editorArticleId}
      onClose={() => setEditorOpen(false)}
      onSaved={(a) => {
        // reflect latest content in local state if present
        if (!a?.id) return;
        const sid = Object.keys(articlesBySuggestion).find(k => articlesBySuggestion[k]?.articleId === a.id || articlesBySuggestion[k]?.article?.id === a.id);
        if (sid) {
          setArticlesBySuggestion(prev => ({
            ...prev,
            [sid]: { ...(prev[sid] || {}), article: { ...(prev[sid]?.article || {} as Record<string, unknown>), ...a }, articleId: a.id }
          }));
        }
      }}
    />
    </>
  );
}
