export default function Hero() {
  return (
    <section className="section">
      <div className="container grid gap-10 md:grid-cols-2 md:items-center">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-xs text-success shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-green-400">
            <span>Early adopters</span>
            <span className="h-1 w-1 rounded-full bg-brand-600" />
            <span>50% Off</span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Dream up premium content ideas for your product.
          </h1>
          <p className="text-lg">
            Turn your product into scroll‑stopping articles and posts — powered by live trends, keywords, and AI.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <a href="#cta" className="inline-flex items-center justify-center rounded-xl bg-brand-600 hover:bg-brand-900 active:scale-[0.98] px-5 py-2 text-sm font-medium">Try the demo</a>
            <a href="#pricing" className="inline-flex items-center justify-center rounded-xl border border-slate-800 px-5 py-2 font-medium hover:bg-slate-900">See pricing</a>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span>⚡ No credit card</span>
            <span>•</span>
            <span>🔒 Your data stays yours</span>
            <span>•</span>
            <span>🚀 2‑min setup</span>
          </div>
        </div>
        <div className="relative">
          <div className="absolute -inset-6 -z-10 rounded-3xl bg-brand-100 blur-2xl" />
          <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-2xl">
            <img src="/window.svg" alt="Dashboard preview" className="w-full rounded-xl" />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <img src="/file.svg" className="rounded-lg border border-slate-200" alt="Summary" />
            <img src="/globe.svg" className="rounded-lg border border-slate-200" alt="Calendar" />
            <img src="/vercel.svg" className="rounded-lg border border-slate-200" alt="Alerts" />
          </div>
        </div>
      </div>
    </section>
  );
}
