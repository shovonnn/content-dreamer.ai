"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/apiClient";
import Hero from "@/components/Hero";
import Logos from "@/components/Logos";
import Features from "@/components/Features";
import Showcase from "@/components/Showcase";
import Pricing from "@/components/Pricing";
import FAQ from "@/components/FAQ";
import Footer from "@/components/Footer";

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
  const res = await api.post(`/api/feeds/initiate`, { product_name: name, product_description: desc, guest_id });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "Failed to initiate report");
  router.push(`/feed/${data.report_id}?guest_id=${encodeURIComponent(guest_id)}`);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="">
      <Hero />
      <section id="cta" className="section">
        <div className="container grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
          <div className="space-y-3">
            <h2 className="text-2xl font-semibold">Try it free</h2>
            <p className="">No login required for your first feed.</p>
            <ul className="mt-2 space-y-1 text-sm">
              <li>• SEO keywords from Google autocomplete</li>
              <li>• Trends and tweets from X/Twitter</li>
              <li>• Medium tags and top articles</li>
            </ul>
          </div>
          <form onSubmit={onSubmit} className="rounded-2xl rounded-xl border border-slate-300 font-medium bg-slate-50 dark:border-slate-800 dark:bg-slate-900 p-6 shadow-sm">
            <label className="block text-sm font-medium">Product name</label>
            <input className="mt-1 w-full rounded-md border px-3 py-2 dark:border-slate-800" placeholder="e.g. Acme Outreach" value={name} onChange={e=>setName(e.target.value)} />
            <label className="block mt-4 text-sm font-medium">Product description</label>
            <textarea className="mt-1 w-full rounded-md border px-3 py-2 h-28 dark:border-slate-800" placeholder="What does it do? Who is it for?" value={desc} onChange={e=>setDesc(e.target.value)} />
            {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
            <button disabled={loading} className="mt-5 inline-flex items-center justify-center rounded-xl bg-brand-600 px-5 py-3 font-medium text-white hover:bg-brand-700 disabled:opacity-50">
              {loading ? "Generating…" : "Get content suggestion"}
            </button>
          </form>
        </div>
      </section>
      <Features />
      <Showcase />
      <Pricing />
      <FAQ />
      <Footer />
    </main>
  );
}
