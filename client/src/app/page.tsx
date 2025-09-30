"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/apiClient";

function ensureGuestId(): string {
  if (typeof window === "undefined") return "";
  const key = "guest_id";
  let id = window.localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(key, id);
    document.cookie = `${key}=${id}; path=/; max-age=${60 * 60 * 24 * 365}`;
  }
  return id;
}

export default function Home() {
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
      const res = await api.post(`/api/reports/initiate`, { product_name: name, product_description: desc, guest_id });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "Failed to initiate report");
      router.push(`/report/${data.report_id}?guest_id=${encodeURIComponent(guest_id)}`);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-gray-900">
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-6xl px-6 pt-16 pb-16">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-5xl font-extrabold tracking-tight leading-tight">Dream up premium content ideas</h1>
              <p className="mt-5 text-xl text-gray-600">Turn your product into scroll‑stopping articles and tweets—powered by trends, keywords, and AI.</p>
              <ul className="mt-6 space-y-2 text-gray-700">
                <li>• SEO keywords from Google autocomplete</li>
                <li>• Trends and tweets from Twitter</li>
                <li>• Medium tags and top articles</li>
              </ul>
            </div>
            <div>
              <form onSubmit={onSubmit} className="rounded-2xl border border-gray-200 p-6 shadow-sm">
                <h2 className="text-2xl font-semibold">Try it free</h2>
                <p className="text-sm text-gray-500 mt-1">No login required for your first report.</p>
                <label className="block mt-5 text-sm font-medium">Product name</label>
                <input className="mt-1 w-full rounded-md border px-3 py-2" placeholder="e.g. Acme Outreach" value={name} onChange={e=>setName(e.target.value)} />
                <label className="block mt-4 text-sm font-medium">Product description</label>
                <textarea className="mt-1 w-full rounded-md border px-3 py-2 h-28" placeholder="What does it do? Who is it for?" value={desc} onChange={e=>setDesc(e.target.value)} />
                {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
                <button disabled={loading} className="mt-5 inline-flex items-center justify-center rounded-md bg-black px-4 py-2 text-white hover:bg-gray-900 disabled:opacity-50">
                  {loading ? "Generating…" : "Generate content ideas"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
