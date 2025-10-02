"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/apiClient";

type Feed = { id: string; status: string; created_on?: string | null; completed_at?: string | null };

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const pid = params.id;
  const [product, setProduct] = useState<{ id: string; name: string; description: string } | null>(null);
  const [latest, setLatest] = useState<Feed | null>(null);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      // load product from list endpoint for now
      const res = await api.get("/api/products");
      const json = await res.json();
      const found = (json.products || []).find((p: any) => p.id === pid) || null;
      if (found) {
        setProduct({ id: found.id, name: found.name, description: found.description });
        setLatest(found.latest_feed || null);
      } else {
        setProduct(null);
      }
      const r2 = await api.get(`/api/products/${pid}/feeds`);
      const j2 = await r2.json();
      setFeeds(j2.feeds || []);
    } catch (e: any) {
      setError(e.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [pid]);

  async function generateNew() {
    setCreating(true);
    setError(null);
    try {
      const res = await api.post(`/api/products/${pid}/feeds/initiate`, {});
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Failed to initiate");
      // navigate to feed page
      window.location.href = `/feed/${json.report_id}`;
    } catch (e: any) {
      setError(e.message || "Failed to initiate");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-gray-900">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Product</h1>
          <Link href="/dashboard" className="text-sm text-gray-600 hover:text-gray-900">Back to dashboard</Link>
        </div>
        {loading && <p className="mt-6 text-gray-600">Loading…</p>}
        {error && <p className="mt-6 text-red-600">{error}</p>}
        {product && (
          <div className="mt-6">
            <div className="rounded-lg border p-5">
              <h2 className="text-xl font-medium">{product.name}</h2>
              <p className="mt-2 text-gray-700 whitespace-pre-wrap">{product.description}</p>
              {latest && (
                <div className="mt-4 rounded-md border p-4 bg-gray-50">
                  <div className="text-sm">Latest feed status: <span className="font-medium">{latest.status}</span></div>
                  <div className="text-xs text-gray-500">{latest.created_on ? new Date(latest.created_on).toLocaleString() : ""}</div>
                </div>
              )}
              <div className="mt-4 flex gap-2">
                <button onClick={generateNew} disabled={creating} className="rounded-md bg-black text-white px-4 py-2 hover:bg-gray-900 disabled:opacity-50">{creating ? "Starting…" : "Generate new feed"}</button>
                {latest && <Link href={`/feed/${latest.id}`} className="rounded-md border px-4 py-2 hover:bg-gray-50">View latest feed</Link>}
              </div>
            </div>
            <div className="mt-8">
              <h3 className="font-semibold">Previous feeds</h3>
              {feeds.length === 0 ? (
                <p className="mt-2 text-gray-600">No previous feeds.</p>
              ) : (
                <ul className="mt-3 divide-y">
                  {feeds.map((f) => (
                    <li key={f.id} className="py-3 flex items-center justify-between">
                      <div>
                        <div className="text-sm">Status: {f.status}</div>
                        <div className="text-xs text-gray-500">{f.created_on ? new Date(f.created_on).toLocaleString() : ""}</div>
                      </div>
                      <Link href={`/feed/${f.id}`} className="text-sm rounded-md border px-3 py-1.5 hover:bg-gray-50">Open</Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
