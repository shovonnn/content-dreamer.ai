export default function Logos() {
  return (
    <section className="section py-10">
      <div className="container text-center space-y-6">
        <p className="text-slate-500">Trusted by lean teams & solo founders</p>
        <div className="flex flex-wrap items-center justify-center gap-8 opacity-70">
          {["Acme","Globex","Soylent","Umbrella","Initech","Hooli"].map((n)=> (
            <div key={n} className="h-6 w-24 rounded bg-slate-200" title={n} />
          ))}
        </div>
      </div>
    </section>
  );
}
