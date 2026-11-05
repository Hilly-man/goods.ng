"use client";

import { RefreshCw } from "lucide-react";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="container-page grid min-h-[50vh] place-items-center py-12 text-center">
      <div>
        <h1 className="text-2xl font-bold">Something went wrong</h1>
        <p className="mt-1 text-muted">This may be a network issue. Please try again.</p>
        <button onClick={reset} className="mt-5 inline-flex items-center gap-2 rounded-lg bg-brand-700 px-5 py-2.5 font-semibold text-white">
          <RefreshCw className="size-4" /> Try again
        </button>
      </div>
    </div>
  );
}
