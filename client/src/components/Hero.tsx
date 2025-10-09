import TryItForm from './TryItForm'

export default function Hero() {
  return (
    <section className="section">
      <div className="container grid gap-20 md:grid-cols-2 md:items-center">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-xs text-success shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-green-400">
            <span>Early adopters</span>
            <span className="h-1 w-1 rounded-full bg-brand-600" />
            <span>50% Off</span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Consistent content strategy is the secret sauce for indie success.
          </h1>
          <p className="text-lg">
            But as a technical person, do you have enough free mental bandwidth to
            keep up with the latest trends, topics, and come up with new ideas? Content Dreamer helps you
            generate fresh, relevant content ideas daily, so you can focus on building in public and engaging with your audience.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <button onClick={() => (document.querySelector("#try-it-form input") as HTMLInputElement)?.focus()} className="inline-flex items-center justify-center rounded-xl bg-brand-600 hover:bg-brand-900 active:scale-[0.98] px-5 py-2 text-sm font-medium">Try the demo</button>
            <a href="#pricing" className="inline-flex items-center justify-center rounded-xl border border-slate-800 px-5 py-2 font-medium hover:bg-slate-900">See pricing</a>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span>⚡ No credit card</span>
            <span>•</span>
            <span>🚀 2‑min setup</span>
          </div>
        </div>
        <div className="relative">
          <div className="absolute -inset-6 -z-10 rounded-3xl" />
          <div className="">
            <div className="relative z-10 overflow-hidden rounded-xl border border-brand-600 dark:bg-slate-800 shadow-[0_20px_50px_rgba(0,_0,_0,_0.25)] ring-primary ring-foreground/10 dark:shadow-[0_20px_50px_rgba(0,_0,_0,_0.5)] dark:ring-primary/25">
              <TryItForm />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
