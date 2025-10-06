function Feature({title, desc, icon}: {title: string; desc: string; icon: string}) {
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
      <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl text-brand-700">
        {icon}
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2">{desc}</p>
    </div>
  );
}

export default function Features() {
  return (
    <section id="features" className="section">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">Everything you need for consistent content strategy</h2>
          <p className="mt-3">Find ideas, plan posts, and publish faster with confidence.</p>
        </div>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          <Feature title="Smart keywords" desc="Pulls SEO terms from live autocomplete to guide topics." icon="🔍" />
          <Feature title="Trend signals" desc="Taps into social chatter to spot what’s resonating now." icon="📈" />
          <Feature title="One‑click briefs" desc="Turn a topic into a brief with outline, hooks and references." icon="📝" />
          <Feature title="Publishing cues" desc="See best times and channels based on your niche." icon="⏰" />
          <Feature title="Team ready" desc="Assign owners and track status from idea to live." icon="👥" />
          <Feature title="AI assist" desc="Ask for angles, titles or tweet threads instantly." icon="🤖" />
        </div>
      </div>
    </section>
  );
}
