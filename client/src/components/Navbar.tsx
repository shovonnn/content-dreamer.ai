"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import { ProfileMenu } from "@/components/ProfileMenu";
import Image from "next/image";

export function Navbar() {
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    const update = () => setAuthed(api.isAuthenticated());
    update();
    api.onAuthChange(update);
    return () => api.offAuthChange(update);
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-white/70 backdrop-blur dark:bg-slate-950/70 border-b border-slate-200/60 dark:border-slate-800/60">
      <div className="container h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Image src={'/icon.png'} width={32} height={32} className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-white" alt="Content Dreamer ai" />
          <span>Content Dreamer</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-sm">
          <Link href="/#features" className="hover:text-brand-600">Features</Link>
          {authed && <Link href="/pricing" className="hover:text-brand-600">Pricing</Link>}
          {!authed && <Link href="/#pricing" className="hover:text-brand-600">Pricing</Link>}
          <Link href="/#faq" className="hover:text-brand-600">FAQ</Link>
          {authed && <Link href="/dashboard" className="hover:text-brand-600">Dashboard</Link>}
        </nav>
        <div className="flex items-center gap-3">
          {authed ? (
            <ProfileMenu />
          ) : (
            <>
              <Link href="/login" className="hidden md:inline kbd border-slate-300 dark:border-slate-700">Log in</Link>
              <Link href="/register" className="inline-flex items-center rounded-xl bg-brand-600 px-4 py-2 text-white hover:bg-brand-700">Get Started</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
