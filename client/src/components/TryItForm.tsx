"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/apiClient";

function ensureGuestId(): string {
  if (typeof window === "undefined") return "";
  const key = "guest_id";
  let id = window.localStorage.getItem(key);
  if (!id) {
    try {
      id = crypto.randomUUID();
    } catch {
      id = Math.random().toString(36).slice(2);
    }
    window.localStorage.setItem(key, id);
    document.cookie = `${key}=${id}; path=/; max-age=${60 * 60 * 24 * 365}`;
  }
  return id;
}

export default function TryItForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name || !desc) {
      setError("Please enter product name and description");
      return;
    }
    setLoading(true);
    try {
      const guest_id = ensureGuestId();
      const res = await api.post(`/api/feeds/initiate`, { product_name: name, product_description: desc, guest_id });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "Failed to initiate report");
      if (data.prompt_login) {
        // redirect to login with next param to add product page
        const next = encodeURIComponent(`/dashboard`);
        window.location.href = `/login?next=${next}`;
        return;
      }
      router.push(`/feed/${data.report_id}?guest_id=${encodeURIComponent(guest_id)}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form id="try-it-form" onSubmit={onSubmit} className="rounded-xl border border-slate-300 font-medium bg-slate-50 dark:border-slate-800 dark:bg-slate-900 p-6 shadow-sm">
      <label className="block text-sm font-medium">Product name</label>
      <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-800" placeholder="e.g. Acme Outreach" value={name} onChange={e=>setName(e.target.value)} />
      <label className="block mt-4 text-sm font-medium">Product description</label>
      <textarea className="mt-1 w-full rounded-md border px-3 py-2 h-28 dark:border-slate-800" placeholder="What does it do? Who is it for?" value={desc} onChange={e=>setDesc(e.target.value)} />
      {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
      <button disabled={loading} className="mt-5 inline-flex items-center justify-center rounded-xl bg-brand-600 px-5 py-3 font-medium text-white hover:bg-brand-700 disabled:opacity-50">
        {loading ? "Generating…" : "Get content suggestion"}
      </button>
    </form>
  );
}
