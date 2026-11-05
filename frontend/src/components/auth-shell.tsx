import { ShieldCheck } from "lucide-react";

export function AuthShell({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="container-page grid min-h-[70vh] place-items-center py-8">
      <div className="w-full max-w-md">
        <div className="card p-6 sm:p-8">
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
          <div className="mt-6">{children}</div>
        </div>
        <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-muted">
          <ShieldCheck className="size-4 text-brand-700" /> Your data is encrypted and never sold.
        </p>
      </div>
    </div>
  );
}
