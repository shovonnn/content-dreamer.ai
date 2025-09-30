export default function PricingPage() {
  return (
    <main className="min-h-screen bg-white text-gray-900">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="text-4xl font-extrabold">Pricing</h1>
        <p className="text-gray-600 mt-2">Pick a plan that fits your growth.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-10">
          {[
            { name: "Basic", price: "$5", features: ["1 product", "1 content/day", "1 article/day"] },
            { name: "Pro", price: "$15", features: ["5 products", "5 content/day", "5 articles/day"] },
            { name: "Advanced", price: "$50", features: ["Unlimited products", "Unlimited content", "Unlimited articles"] },
          ].map((p) => (
            <div key={p.name} className="rounded-2xl border p-6">
              <h3 className="text-xl font-semibold">{p.name}</h3>
              <div className="text-3xl font-bold mt-2">{p.price}<span className="text-base font-normal text-gray-500">/mo</span></div>
              <ul className="mt-4 space-y-1 text-gray-700">
                {p.features.map((f) => <li key={f}>• {f}</li>)}
              </ul>
              <button className="mt-6 w-full rounded-md bg-black text-white py-2.5 hover:bg-gray-900">Choose {p.name}</button>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
