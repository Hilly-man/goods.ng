export function ProsePage({ title, intro, updated, children }: { title: string; intro?: string; updated?: string; children: React.ReactNode }) {
  return (
    <div className="container-page py-6 sm:py-10">
      <article className="card mx-auto max-w-3xl p-5 sm:p-10">
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{title}</h1>
        {updated && <p className="mt-1 text-xs text-muted">Last updated {updated}</p>}
        {intro && <p className="mt-3 text-lg text-ink/80">{intro}</p>}
        <div className="prose-page mt-4">{children}</div>
      </article>
    </div>
  );
}
