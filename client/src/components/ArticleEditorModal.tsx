"use client";
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/apiClient";

// Load the editor only on the client to avoid SSR issues
const MDEditor = dynamic(() => import("@uiw/react-md-editor"), { ssr: false });

export type ArticleData = {
  id: string;
  title: string;
  content_md?: string | null;
  content_html?: string | null;
  status: string;
  error?: string | null;
};

type Props = {
  isOpen: boolean;
  articleId?: string | null;
  onClose: () => void;
  onSaved?: (article: ArticleData) => void;
};

export default function ArticleEditorModal({ isOpen, articleId, onClose, onSaved }: Props) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [md, setMd] = useState<string>("");

  useEffect(() => {
    let abort = false;
    async function fetchArticle(aid: string) {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get(`/api/articles/${aid}`);
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error || "Failed to load article");
        if (abort) return;
        setTitle(json.title || "");
        // Prefer markdown if available
        setMd((json.content_md as string) || "");
      } catch (e: unknown) {
        if (!abort) setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (!abort) setLoading(false);
      }
    }
    if (isOpen && articleId) {
      fetchArticle(articleId);
    } else if (!isOpen) {
      // reset on close
      setTitle("");
      setMd("");
      setError(null);
      setLoading(false);
      setSaving(false);
    }
    return () => {
      abort = true;
    };
  }, [isOpen, articleId]);

  async function handleSave() {
    if (!articleId) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api.put(`/api/articles/${articleId}`, { title, content_md: md });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Failed to save");
      onSaved?.(json as ArticleData);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-[min(980px,95vw)] max-h-[90vh] overflow-hidden rounded-xl border border-slate-700 bg-white dark:bg-slate-900 shadow-lg">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-lg font-semibold">Edit Article</h3>
          <button onClick={onClose} className="text-sm px-2 py-1 rounded-md border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800">Close</button>
        </div>
        <div className="p-4 space-y-3" data-color-mode="dark">
          {error && <div className="text-sm text-red-600">{error}</div>}
          {loading ? (
            <div className="text-sm text-slate-500">Loading…</div>
          ) : (
            <>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Title"
                className="w-full rounded-md border px-3 py-2 bg-transparent border-slate-300 dark:border-slate-700"
              />
              <MDEditor value={md} onChange={(v: string | undefined) => setMd(v || "")} height={480} />
            </>
          )}
        </div>
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-slate-200 dark:border-slate-800">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-md border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800">Cancel</button>
          <button onClick={handleSave} disabled={saving || loading} className="px-4 py-2 text-sm rounded-md bg-brand-600 border border-brand-600 text-white hover:bg-brand-700 disabled:opacity-50">{saving ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </div>
  );
}
