"use client";
import { useState } from "react";
import { api } from "@/lib/apiClient";

export default function BillingPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function openPortal() {
    setError(null);
    if (!api.isAuthenticated()) {
      const next = encodeURIComponent("/billing");
      window.location.href = `/login?next=${next}`;
      return;
    }
    setLoading(true);
    try {
      const res = await api.post("/api/billing/portal", {});
      const json = await res.json();
      if (!res.ok || !json.url) throw new Error(json?.error || "Could not open portal");
      window.location.href = json.url;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to open portal";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-gray-900">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <h1 className="text-3xl font-bold">Billing</h1>
        <p className="mt-2 text-gray-600">Manage your subscription and payment methods.</p>
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        <button onClick={openPortal} disabled={loading} className="mt-6 rounded-md bg-black text-white px-4 py-2 disabled:opacity-50">
          {loading ? "Opening…" : "Manage billing"}
        </button>
      </div>
    </main>
  );
}
