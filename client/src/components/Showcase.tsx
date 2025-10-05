export default function Showcase() {
  return (
    <section className="section">
      <div className="container grid items-center gap-10 md:grid-cols-2">
        <div className="order-2 md:order-1 space-y-4">
          <h3 className="text-2xl font-semibold">See your content plan, at a glance</h3>
          <p className="text-slate-600">Live boards show ideas by channel and status. Drill into performance in one click.</p>
          <ul className="list-disc pl-5 text-slate-600">
            <li>Owner‑based approvals</li>
            <li>Multi‑channel scheduling</li>
            <li>CSV export + Slack ping</li>
          </ul>
        </div>
        <div className="order-1 md:order-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-xl">
            <img src="/window.svg" alt="Plan chart" className="w-full rounded-lg" />
          </div>
        </div>
      </div>
    </section>
  );
}
