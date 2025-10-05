const faqs = [
  { q: "Do you store my account credentials?", a: "No. We connect to providers only when needed and store content ideas and metadata." },
  { q: "Can I import from CSV?", a: "Yes. Upload a CSV or paste links to seed your first board." },
  { q: "Do you support teams?", a: "Invite teammates, set owners, and track status together." },
];

export default function FAQ(){
  return (
    <section id="faq" className="section">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">Common questions</h2>
        </div>
        <div className="mx-auto mt-8 max-w-3xl divide-y divide-slate-200 rounded-2xl border border-slate-200 dark:border-slate-800 dark:divide-slate-800 dark:bg-slate-900">
          {faqs.map((f) => (
            <details key={f.q} className="group p-6">
              <summary className="cursor-pointer list-none text-lg font-medium flex items-center justify-between">
                {f.q}
                <span className="ml-4 inline-block rotate-0 transition group-open:-rotate-180">▾</span>
              </summary>
              <p className="mt-3">{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
