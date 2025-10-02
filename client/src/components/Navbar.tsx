"use client";
import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import { ProfileMenu } from "@/components/ProfileMenu";

export function Navbar() {
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    const update = () => setAuthed(api.isAuthenticated());
    update();
    api.onAuthChange(update);
    return () => api.offAuthChange(update);
  }, []);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-gray-200 bg-white">
      <div className="mx-auto max-w-6xl px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/next.svg" alt="Content Dreamer" width={28} height={28} className="dark:invert" />
          <span className="font-semibold text-lg tracking-tight text-gray-900">Content Dreamer</span>
        </Link>
        <nav className="flex items-center gap-3">
          <Link href="/dashboard" className="text-sm text-gray-900 hover:text-black">Dashboard</Link>
          <Link href="/pricing" className="text-sm text-gray-900 hover:text-black">Pricing</Link>
          {authed ? (
            <ProfileMenu />
          ) : (
            <>
              <Link href="/login" className="text-sm px-3 py-1.5 rounded-md hover:bg-gray-50 text-gray-900">Login</Link>
              <Link href="/register" className="text-sm px-3 py-1.5 rounded-md bg-black text-white hover:bg-gray-900">Get Started</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
