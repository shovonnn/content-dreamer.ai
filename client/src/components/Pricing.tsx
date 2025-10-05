function Tier({name, price, features}:{name:string; price:string; features:string[]}){
  return (
    <div className="flex flex-col rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
      <h3 className="text-xl font-semibold">{name}</h3>
      <div className="mt-2 text-3xl font-bold">{price}</div>
      <ul className="mt-4 space-y-2">
        {features.map(f=> <li key={f}>✓ {f}</li>)}
      </ul>
      <a href="#cta" className="mt-6 inline-flex items-center justify-center rounded-xl bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700">Start free</a>
    </div>
  );
}

export default function Pricing(){
  return (
    <section id="pricing" className="section">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">Fair pricing</h2>
          <p className="mt-3">Simple plans that scale when you do.</p>
        </div>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          <Tier name="Hobby" price="$0" features={["10 ideas/day", "Email export", "1 workspace"]} />
          <Tier name="Pro" price="$19/mo" features={["Unlimited ideas", "Team owners", "Slack alerts"]} />
          <Tier name="Team" price="$49/mo" features={["Everything in Pro", "SSO", "Priority support"]} />
        </div>
      </div>
    </section>
  );
}
