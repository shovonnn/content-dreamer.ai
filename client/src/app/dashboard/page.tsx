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
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
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

  async function addProduct(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name || !desc) {
      setError("Enter product name and description");
      return;
    }
    try {
      const res = await api.post("/api/products", { name, description: desc });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Create failed");
      setName("");
      setDesc("");
      await load();
    } catch (e: any) {
      setError(e.message || "Create failed");
    }
  }

  return (
    <main className="min-h-screen bg-white text-gray-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <Link href="/" className="text-sm text-gray-600 hover:text-gray-900">Home</Link>
        </div>
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-10">
          <section className="md:col-span-2">
            <h2 className="text-xl font-semibold">Products</h2>
            {loading ? (
              <p className="mt-3 text-gray-600">Loading…</p>
            ) : products.length === 0 ? (
              <p className="mt-3 text-gray-600">No products yet.</p>
            ) : (
              <ul className="mt-4 divide-y">
                {products.map((p) => (
                  <li key={p.id} className="py-4 flex items-start justify-between">
                    <div>
                      <Link href={`/product/${p.id}`} className="font-medium hover:underline">{p.name}</Link>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">{p.description}</p>
                      {p.latest_feed && (
                        <div className="mt-2 text-xs text-gray-500">Latest feed: {p.latest_feed.status} {p.latest_feed.created_on ? `• ${new Date(p.latest_feed.created_on).toLocaleString()}` : ""}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Link href={`/product/${p.id}`} className="text-sm rounded-md border px-3 py-1.5 hover:bg-gray-50">View</Link>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h2 className="text-xl font-semibold">Add product</h2>
            <form onSubmit={addProduct} className="mt-4 rounded-lg border p-4">
              <label className="block text-sm font-medium">Name</label>
              <input className="mt-1 w-full rounded-md border px-3 py-2" value={name} onChange={e=>setName(e.target.value)} />
              <label className="block text-sm font-medium mt-4">Description</label>
              <textarea className="mt-1 w-full rounded-md border px-3 py-2 h-28" value={desc} onChange={e=>setDesc(e.target.value)} />
              {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
              <button className="mt-4 w-full rounded-md bg-black text-white px-3 py-2 hover:bg-gray-900">Add</button>
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}
