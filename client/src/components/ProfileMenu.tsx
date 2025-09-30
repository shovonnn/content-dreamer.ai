"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/apiClient";

type Me = { id: string; name: string | null; email: string | null; avatar_url?: string | null };

export function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get("/api/me");
        if (res.ok) {
          const data = await res.json();
          setMe(data as Me);
        }
      } catch {
        // ignore
      }
    }
    load();
  }, []);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const avatar = me?.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(me?.name || me?.email || "U")}`;

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(v => !v)} className="flex items-center gap-2 text-gray-900">
        <img src={avatar} alt="avatar" className="w-8 h-8 rounded-full border" />
        <span className="text-sm">{me?.name || me?.email || "Account"}</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-56 rounded-xl border bg-white shadow-lg p-2 z-50">
          <div className="px-3 py-2">
            <div className="text-sm font-medium text-gray-900">{me?.name || "Your account"}</div>
            <div className="text-xs text-gray-600 truncate">{me?.email}</div>
          </div>
          <div className="my-1 h-px bg-gray-100" />
          <Link href="/dashboard" className="block px-3 py-2 text-sm rounded-md hover:bg-gray-50 text-gray-900">Dashboard</Link>
          <Link href="/billing" className="block px-3 py-2 text-sm rounded-md hover:bg-gray-50 text-gray-900">Billing</Link>
          <Link href="/settings" className="block px-3 py-2 text-sm rounded-md hover:bg-gray-50 text-gray-900">Settings</Link>
          <div className="my-1 h-px bg-gray-100" />
          <button onClick={() => api.logout()} className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-gray-50 text-gray-900">Log out</button>
        </div>
      )}
    </div>
  );
}
