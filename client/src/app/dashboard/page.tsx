"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";

type Product = {
  id: string;
  name: string;
  description: string;
  latest_feed?: { id: string; status: string; created_on?: string | null } | null;
};

export default function DashboardPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const res = await api.get("/api/products");
      const json = await res.json();
      setProducts(json.products || []);
    } catch (e: any) {
      setError(e.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <div className="flex items-center gap-3">
            <Link href="/product/new" className="rounded-md bg-brand-600 text-sm px-3 py-2 hover:bg-brand-700">Add New Product</Link>
          </div>
        </div>
        <section className="mt-8 border border-slate-200 rounded-xl p-6 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
          {error && <p className="mt-3 text-red-600">{error}</p>}
          {loading ? (
            <p className="mt-3 text-gray-600">Loading…</p>
          ) : products.length === 0 ? (
            <p className="mt-3 text-gray-600">No products yet.</p>
          ) : (
            <ul className="mt-4 divide-y divide-slate-200 dark:divide-slate-800">
              {products.map((p) => (
                <li key={p.id} className="py-4 flex items-start justify-between">
                  <div>
                    <Link href={`/product/${p.id}`} className="font-medium hover:underline">{p.name}</Link>
                    <p className="text-sm mt-1 line-clamp-2">{p.description}</p>
                    {p.latest_feed && (
                      <div className="mt-2 text-xs text-gray-500">Latest feed: {p.latest_feed.status} {p.latest_feed.created_on ? `• ${new Date(p.latest_feed.created_on).toLocaleString()}` : ""}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Link href={`/product/${p.id}`} className="text-sm rounded-md border px-3 py-1.5 hover:bg-slate-500">View</Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
