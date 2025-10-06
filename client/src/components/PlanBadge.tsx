"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";

export default function PlanBadge() {
  const [plan, setPlan] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      if (!api.isAuthenticated()) return;
      try {
        const res = await api.get("/api/me/limits");
        const json = await res.json();
        if (res.ok) setPlan(json.plan_id);
      } catch {}
    })();
  }, []);
  if (!plan) return null;
  const name = plan === "free" ? "Free" : plan === "pro" ? "Pro" : plan === "advanced" ? "Advanced" : plan;
  return (
    <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs">
      <span className="opacity-60">Plan:</span>
      <strong>{name}</strong>
      <a className="underline opacity-80 hover:opacity-100" href="/pricing">Manage</a>
    </div>
  );
}
