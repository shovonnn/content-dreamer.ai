export default function Footer(){
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 py-10">
      <div className="container flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3 text-sm">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-white">CD</span>
          <span className="text-slate-500">© {new Date().getFullYear()} Content Dreamer</span>
        </div>
        <nav className="flex gap-4 text-sm text-slate-500">
          <a href="/privacy">Privacy</a>
          <a href="/terms">Terms</a>
          <a href="https://x.com/content_dreamer">Contact</a>
        </nav>
      </div>
    </footer>
  );
}
