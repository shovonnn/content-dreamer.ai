const faqs = [
  {
    q: "What can I generate with Content Dreamer?",
    a: "Tweets and threads, blog post ideas, memes, and short 'AI slop' videos (funny or branded reels) tailored to your niche.",
  },
  {
    q: "Where do ideas come from?",
    a: "We track live trends, news, and search signals plus your keywords to surface timely concepts and angles.",
  },
  {
    q: "How fresh are the trends?",
    a: "Boards update throughout the day as new stories break; regenerate any card to get the latest context.",
  },
  {
    q: "Do you store my social account credentials?",
    a: "No. We only store your generated ideas and board metadata. Any connected accounts use tokens you can revoke at any time.",
  },
  {
    q: "Can I import topics or links to seed a board?",
    a: "Yes. Paste links or upload a CSV to jump-start ideation with your sources.",
  },
  {
    q: "Can I set my brand voice?",
    a: "Yes. Choose tone, audience, and style guidelines; we remember them per workspace to keep outputs on-brand.",
  },
  {
    q: "What is an AI slop video?",
    a: "A fast-cut, meme-style reel with punchy captions and b‑roll. Provide a topic and we generate a short, funny or branded clip.",
  },
  {
    q: "Do you support teams?",
    a: "Invite teammates, assign owners, and track status across boards together.",
  },
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
