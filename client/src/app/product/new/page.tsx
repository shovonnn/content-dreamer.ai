"use client";
import { useState } from "react";
import { api } from "@/lib/apiClient";

export default function NewProductPage() {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name || !desc) {
      setError("Please enter product name and description");
      return;
    }
    setLoading(true);
    try {
      // Create product
      const r1 = await api.post(`/api/products`, { name, description: desc });
      const p: { id: string; error?: string } = await r1.json();
      if (!r1.ok) throw new Error(p?.error || "Failed to create product");
      // Initiate feed for this product
      const r2 = await api.post(`/api/products/${p.id}/feeds/initiate`, {});
      const f: { report_id?: string; error?: string } = await r2.json();
      if (r2.status === 402) {
        const msg = f?.error || "Limit reached";
        window.location.href = `/pricing?reason=${encodeURIComponent(msg)}`;
        return;
      }
      if (!r2.ok) throw new Error(f?.error || "Failed to start feed");
      // Redirect to new feed page
      window.location.href = `/feed/${f.report_id}`;
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Something went wrong";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="">
      <div className="mx-auto max-w-xl px-6 py-10">
        <h1 className="text-2xl font-semibold">Add New Product</h1>
        <form onSubmit={onSubmit} className="mt-6 rounded-xl border p-6 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 shadow-sm">
          <label className="block text-sm font-medium">Product name</label>
          <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-800 bg-slate-50 dark:bg-slate-900" value={name} onChange={e=>setName(e.target.value)} />
          <label className="block text-sm font-medium mt-4">Product description</label>
          <textarea className="mt-1 w-full rounded-md border px-3 py-2 h-28 dark:border-slate-800 bg-slate-50 dark:bg-slate-900" value={desc} onChange={e=>setDesc(e.target.value)} />
          {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
          <div className="mt-6 flex items-center gap-2">
            <button disabled={loading} className="rounded-md bg-brand-600 px-4 py-2 hover:bg-brand-700 disabled:opacity-50 cursor-pointer">{loading ? "Creating…" : "Create & Generate Feed"}</button>
            <a href="/dashboard" className="text-sm hover:text-gray-500">Cancel</a>
          </div>
        </form>
      </div>
    </main>
  );
}
