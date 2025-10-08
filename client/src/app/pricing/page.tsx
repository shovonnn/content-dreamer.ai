"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";

type Plan = {
  id: "free" | "pro" | "advanced" | string;
  price_usd: number;
  limits: {
    products_per_user: number;
    content_generations_per_day: number;
    articles_per_day: number;
    videos_per_day: number;
  };
};

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePlanId, setActivePlanId] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState<{ visible: boolean; targetPlanId?: string } | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        // Load plans (public)
        const res = await api.get("/api/plans", { skipAuth: true });
        const json = await res.json();
        setPlans(json);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Failed to load plans";
        setError(msg);
      }
      // Try to load current plan without triggering login redirect
      try {
        const meRes = await api.get(`/api/me/limits`);
        if (meRes.ok) {
          const me = await meRes.json();
          if (me?.plan_id) setActivePlanId(me.plan_id as string);
        }
      } catch {
        // ignore; user may be logged out
      }
    })();
  }, []);

  async function choose(planId: string) {
    setError(null);
    // If already on this plan, do nothing
    if (activePlanId && planId === activePlanId) return;

    // If selecting Free while on paid, confirm downgrade and open portal
    if (planId === "free" && (activePlanId === "pro" || activePlanId === "advanced")) {
      setShowConfirm({ visible: true, targetPlanId: planId });
      return;
    }

    if (planId === "free") {
      // Not subscribed or not logged in → just go to dashboard
      window.location.href = "/dashboard";
      return;
    }
    if (!api.isAuthenticated()) {
      const next = encodeURIComponent("/pricing");
      window.location.href = `/login?next=${next}`;
      return;
    }
    setLoading(true);
    try {
      const res = await api.post("/api/billing/checkout", { plan_id: planId });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Unable to start checkout");
      if (!json.url && json.success) {
        // No URL means upgrade/downgrade to this plan
        setActivePlanId(planId);
        return;
      }
      window.location.href = json.url;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Checkout failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function openPortal() {
    // Open Stripe billing portal (manage/cancel/change plan)
    if (!api.isAuthenticated()) {
      const next = encodeURIComponent("/pricing");
      window.location.href = `/login?next=${next}`;
      return;
    }
    setPortalLoading(true);
    try {
      const res = await api.post("/api/billing/portal", {});
      const json = await res.json();
      if (!res.ok || !json.url) throw new Error(json?.error || "Could not open portal");
      window.location.href = json.url;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to open portal";
      setError(msg);
    } finally {
      setPortalLoading(false);
    }
  }

  return (
    <main className="">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="text-4xl font-extrabold">Pricing</h1>
        <p className="text-gray-600 mt-2">Pick a plan that fits your growth.</p>
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-10">
          {plans.map((p) => {
            const name = p.id === "free" ? "Free" : p.id === "pro" ? "Pro" : p.id === "advanced" ? "Advanced" : p.id;
            const price = p.price_usd === 0 ? "$0" : `$${p.price_usd}`;
            const features = [
              `${p.limits.products_per_user < 0 ? "Unlimited" : p.limits.products_per_user} product${p.limits.products_per_user === 1 ? "" : "s"}`,
              `${p.limits.content_generations_per_day < 0 ? "Unlimited" : p.limits.content_generations_per_day}  idea feeds/day`,
              `${p.limits.articles_per_day < 0 ? "Unlimited" : p.limits.articles_per_day} content generation${p.limits.articles_per_day === 1 ? "" : "s"}/day`,
              `${p.limits.videos_per_day < 0 ? "Unlimited" : p.limits.videos_per_day} video generation${p.limits.videos_per_day === 1 ? "" : "s"}/day`,
            ];
            const isActive = !!activePlanId && p.id === activePlanId;
            return (
              <div key={p.id} className="rounded-2xl border p-6 dark:border-slate-800 dark:bg-slate-900 shadow-sm">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-semibold">{name}</h3>
                  {isActive && <span className="text-xs rounded-full border px-2 py-0.5">Current plan</span>}
                </div>
                <div className="text-3xl font-bold mt-2">{price}<span className="text-base font-normal">/mo</span></div>
                <ul className="mt-4 space-y-1">
                  {features.map((f) => <li key={f}>• {f}</li>)}
                </ul>
                <button onClick={() => choose(p.id)} disabled={loading || isActive} className={`mt-6 w-full rounded-md py-2.5 disabled:opacity-50 ${isActive ? "bg-gray-300 text-gray-700" : "bg-black text-white hover:bg-gray-900"}`}>
                  {isActive ? "Current" : p.id === "free" ? "Use Free" : `Choose ${name}`}
                </button>
              </div>
            );
          })}
        </div>

        {/* Billing management (only for paid plans) */}
        {(activePlanId === "pro" || activePlanId === "advanced") && (
          <div className="mt-12 rounded-xl border p-6 dark:border-slate-800 dark:bg-slate-900 shadow-sm">
            <h2 className="text-xl font-semibold">Manage your subscription</h2>
            <p className="mt-2">Open the billing portal to change plan, update payment method, or cancel.</p>
            <button onClick={openPortal} disabled={portalLoading} className="mt-4 rounded-md bg-black text-white px-4 py-2 disabled:opacity-50">
              {portalLoading ? "Opening…" : "Manage billing"}
            </button>
          </div>
        )}
      </div>

      {/* Confirm downgrade modal */}
      {showConfirm?.visible && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold">Confirm downgrade</h3>
            <p className="mt-2 text-sm text-gray-700">Downgrading to the Free plan will cancel your paid subscription and reduce your daily limits. You can manage or cancel in the billing portal. Continue?</p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button onClick={() => setShowConfirm(null)} className="rounded-md border px-4 py-2">Cancel</button>
              <button onClick={() => { setShowConfirm(null); openPortal(); }} className="rounded-md bg-black text-white px-4 py-2">Yes, open billing</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
