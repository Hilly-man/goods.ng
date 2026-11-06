import { ShieldCheck } from "lucide-react";
import { AfricaSkyline } from "./africa-skyline";

/**
 * Sign in / sign up frame: the card floats over the African skyline, which fills the bottom of the screen.
 * The regular site footer is hidden on these pages (see `[data-auth-screen]` in globals.css).
 */
export function AuthShell({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div data-auth-screen className="relative isolate flex min-h-[calc(100dvh-4rem)] flex-col overflow-hidden bg-gradient-to-b from-canvas via-canvas to-brand-50/70 pb-16 md:pb-0">
      <div className="container-page relative z-10 grid flex-1 place-items-center pb-24 pt-8 sm:pb-36 lg:pb-44">
        <div className="w-full max-w-md">
          <div className="card p-6 shadow-xl shadow-brand-900/5 sm:p-8">
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
            <div className="mt-6">{children}</div>
          </div>
          <p className="mx-auto mt-4 flex w-fit items-center justify-center gap-1.5 rounded-full bg-white/80 px-3 py-1 text-xs text-muted backdrop-blur">
            <ShieldCheck className="size-4 text-brand-700" /> Your data is encrypted and never sold.
          </p>
        </div>
      </div>
      <div className="pointer-events-none absolute inset-x-0 bottom-16 md:bottom-0">
        <AfricaSkyline className="" />
      </div>
    </div>
  );
}
